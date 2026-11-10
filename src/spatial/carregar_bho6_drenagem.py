import os
from pathlib import Path

import geopandas as gpd
import pandas as pd
import requests
import time

from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from shapely.geometry import (
    LineString,
    MultiLineString,
    GeometryCollection,
)

from dotenv import load_dotenv

from sqlalchemy import create_engine
from sqlalchemy import URL
from sqlalchemy import text

from geoalchemy2 import Geometry

# ============================================================
# SERVIÇO BHO6 / ANA-SNIRH
# ============================================================

BHO6_URL = (
    "https://portal1.snirh.gov.br/server/rest/services/"
    "Hosted/main_geoft_bho6_trecho_drenagem/"
    "FeatureServer/0/query"
)


# ============================================================
# CONFIGURAÇÕES
# ============================================================

ROOT_DIR = Path(__file__).resolve().parents[2]


URL_BHO6 = (
    "https://portal1.snirh.gov.br/server/rest/services/"
    "Hosted/main_geoft_bho6_trecho_drenagem/"
    "FeatureServer/0/query"
)

def criar_sessao_http():

    retry = Retry(
        total=3,
        connect=3,
        read=3,
        status=3,
        backoff_factor=2,
        status_forcelist=[
            429,
            500,
            502,
            503,
            504,
        ],
        allowed_methods=[
            "GET",
        ],
    )

    adapter = HTTPAdapter(
        max_retries=retry
    )

    session = requests.Session()

    session.mount(
        "https://",
        adapter,
    )

    return session


SESSION = criar_sessao_http()

CRS_ORIGINAL = 4674

CRS_METRICO = 5880


BUFFER_ANALISE_M = 2000


# ------------------------------------------------------------
# IMPORTANTE
#
# Para o PRIMEIRO TESTE deixe 1.
#
# Depois que tudo funcionar:
#
# LIMITE_MUNICIPIOS = 20
# ------------------------------------------------------------

LIMITE_MUNICIPIOS = 20


TAMANHO_PAGINA = 2000


# ============================================================
# BANCO
# ============================================================

load_dotenv(
    ROOT_DIR / ".env"
)


url = URL.create(

    drivername="postgresql+psycopg",

    username=os.getenv("DB_USER"),

    password=os.getenv("DB_PASSWORD"),

    host=os.getenv("DB_HOST"),

    port=int(
        os.getenv(
            "DB_PORT",
            5433,
        )
    ),

    database=os.getenv("DB_NAME"),
)


engine = create_engine(
    url,
    pool_pre_ping=True,
)


# ============================================================
# FUNÇÕES
# ============================================================

def converter_multilinha(geom):
    """
    Garante MultiLineString.
    Remove geometrias que não possuem componente linear.
    """

    if geom is None:
        return None

    if geom.is_empty:
        return None


    if isinstance(
        geom,
        LineString,
    ):

        return MultiLineString(
            [geom]
        )


    if isinstance(
        geom,
        MultiLineString,
    ):

        return geom


    if isinstance(
        geom,
        GeometryCollection,
    ):

        linhas = []

        for parte in geom.geoms:

            if isinstance(
                parte,
                LineString,
            ):

                linhas.append(
                    parte
                )

            elif isinstance(
                parte,
                MultiLineString,
            ):

                linhas.extend(
                    list(
                        parte.geoms
                    )
                )


        if linhas:

            return MultiLineString(
                linhas
            )


    return None


def requisicao_bho6(
    params,
    tentativas=4,
):

    ultimo_erro = None

    for tentativa in range(
        1,
        tentativas + 1,
    ):

        try:

            resposta = SESSION.get(
                BHO6_URL,
                params=params,

                # 20 s para conectar
                # 120 s para receber os dados
                timeout=(
                    20,
                    120,
                ),
            )

            resposta.raise_for_status()

            dados = resposta.json()

            if (
                isinstance(dados, dict)
                and
                "error" in dados
            ):

                raise RuntimeError(
                    dados["error"]
                )

            return dados

        except (
            requests.exceptions.ReadTimeout,
            requests.exceptions.ConnectTimeout,
            requests.exceptions.ConnectionError,
            requests.exceptions.HTTPError,
            RuntimeError,
        ) as erro:

            ultimo_erro = erro

            if tentativa < tentativas:

                espera = (
                    tentativa * 5
                )

                print(
                    f"  SNIRH demorou para responder. "
                    f"Nova tentativa em {espera}s "
                    f"({tentativa}/{tentativas})..."
                )

                time.sleep(
                    espera
                )

            else:

                break

    raise RuntimeError(
        "Não foi possível consultar a BHO6 "
        "após várias tentativas."
    ) from ultimo_erro


def consultar_bho6_bbox(
    bbox,
):

    xmin = float(
        bbox[0]
    )

    ymin = float(
        bbox[1]
    )

    xmax = float(
        bbox[2]
    )

    ymax = float(
        bbox[3]
    )


    # --------------------------------------------------------
    # ETAPA 1
    # Buscar somente os IDs dos trechos
    # --------------------------------------------------------

    params_ids = {

        "where":
            "1=1",

        "geometry":
            (
                f"{xmin},"
                f"{ymin},"
                f"{xmax},"
                f"{ymax}"
            ),

        "geometryType":
            "esriGeometryEnvelope",

        "inSR":
            "4674",

        "spatialRel":
            "esriSpatialRelIntersects",

        "returnIdsOnly":
            "true",

        "returnGeometry":
            "false",

        "f":
            "json",
    }


    dados_ids = requisicao_bho6(
        params_ids
    )


    ids = (
        dados_ids.get(
            "objectIds"
        )
        or
        []
    )


    if not ids:

        print(
            "  Nenhum trecho BHO6 "
            "encontrado."
        )

        return []


    ids = sorted(
        ids
    )


    print(
        f"  Trechos BHO6 encontrados: "
        f"{len(ids)}"
    )


    # --------------------------------------------------------
    # ETAPA 2
    # Baixar as geometrias em pequenos lotes
    # --------------------------------------------------------

    TAMANHO_LOTE = 200

    features = []


    for inicio in range(
        0,
        len(ids),
        TAMANHO_LOTE,
    ):

        lote_ids = ids[
            inicio:
            inicio + TAMANHO_LOTE
        ]


        params_features = {

            "where":
                "1=1",

            "objectIds":
                ",".join(
                    str(valor)
                    for valor
                    in lote_ids
                ),

            "outFields":
                "*",

            "returnGeometry":
                "true",

            "outSR":
                "4674",

            "f":
                "geojson",
        }


        dados = requisicao_bho6(
            params_features
        )


        lote_features = (
            dados.get(
                "features"
            )
            or
            []
        )


        features.extend(
            lote_features
        )


        print(
            "  Baixando trechos: "
            f"{min(inicio + TAMANHO_LOTE, len(ids))}"
            f"/{len(ids)}"
        )


    # --------------------------------------------------------
    # Remover eventuais duplicidades
    # --------------------------------------------------------

    features_unicas = {}

    features_sem_id = []


    for feature in features:

        propriedades = (
            feature.get(
                "properties",
                {}
            )
        )


        fid = (
            propriedades.get(
                "fid"
            )
        )


        if fid is None:

            features_sem_id.append(
                feature
            )

        else:

            features_unicas[
                fid
            ] = feature


    resultado = (
        list(
            features_unicas.values()
        )
        +
        features_sem_id
    )


    print(
        f"  Trechos recebidos: "
        f"{len(resultado)}"
    )


    return resultado


# ============================================================
# MUNICÍPIOS ALVO
# ============================================================

sql_municipios = f"""
SELECT

    codigo_ibge,

    nome_municipio,

    rank_ipa,

    ipa,

    geom

FROM spatial.municipio_alvo

ORDER BY rank_ipa

LIMIT {LIMITE_MUNICIPIOS};
"""


municipios = gpd.read_postgis(

    sql_municipios,

    engine,

    geom_col="geom",
)


print("=" * 72)
print("VERDEPRIORIZA - BHO6")
print("=" * 72)

print(
    f"\nMunicípios a processar: "
    f"{len(municipios)}"
)


# ============================================================
# LIMPAR CARGA ANTERIOR
# ============================================================

codigos = (
    municipios[
        "codigo_ibge"
    ]

    .tolist()
)


with engine.begin() as conn:

    conn.execute(

        text("""
        DELETE
        FROM spatial.bho6_drenagem_alvo
        WHERE codigo_ibge = ANY(:codigos);
        """),

        {
            "codigos":
                codigos
        },
    )


# ============================================================
# PROCESSAMENTO
# ============================================================

session_frames = []


for _, municipio in municipios.iterrows():

    codigo = municipio[
        "codigo_ibge"
    ]

    nome = municipio[
        "nome_municipio"
    ]


    print(
        "\n" + "-" * 72
    )

    print(
        f"Município: {nome}"
    )

    print(
        f"Código IBGE: {codigo}"
    )


    # --------------------------------------------------------
    # GEOMETRIA MUNICIPAL EM CRS MÉTRICO
    # --------------------------------------------------------

    municipio_gdf = gpd.GeoDataFrame(

        [
            {
                "codigo_ibge":
                    codigo,

                "geometry":
                    municipio["geom"],
            }
        ],

        crs="EPSG:4674",
    )


    municipio_5880 = (
        municipio_gdf
        .to_crs(
            epsg=CRS_METRICO
        )
    )


    # --------------------------------------------------------
    # BUFFER DE CONTEXTO
    # --------------------------------------------------------

    geom_buffer_5880 = (

        municipio_5880
        .geometry
        .iloc[0]
        .buffer(
            BUFFER_ANALISE_M
        )
    )


    buffer_gdf = gpd.GeoDataFrame(

        [
            {
                "geometry":
                    geom_buffer_5880
            }
        ],

        crs="EPSG:5880",
    )


    buffer_4674 = (

        buffer_gdf

        .to_crs(
            epsg=CRS_ORIGINAL
        )

    )


    bbox = (
        buffer_4674
        .total_bounds
    )


    # --------------------------------------------------------
    # CONSULTAR ANA
    # --------------------------------------------------------

    features = consultar_bho6_bbox(
        bbox
    )


    print(
        f"Trechos recuperados no envelope: "
        f"{len(features):,}"
    )


    if not features:

        print(
            "Nenhum trecho encontrado."
        )

        continue


    drenagem = (

        gpd.GeoDataFrame
        .from_features(
            features,
            crs="EPSG:4674",
        )
    )


    # --------------------------------------------------------
    # CLIP EXATO AO BUFFER
    # --------------------------------------------------------

    drenagem = gpd.clip(

        drenagem,

        buffer_4674,
    )


    drenagem = drenagem[
        ~drenagem.geometry.is_empty
    ].copy()


    # --------------------------------------------------------
    # NORMALIZAR GEOMETRIAS
    # --------------------------------------------------------

    drenagem[
        "geometry"
    ] = (

        drenagem.geometry

        .apply(
            converter_multilinha
        )
    )


    drenagem = drenagem[
        drenagem.geometry.notna()
    ].copy()


    print(
        f"Trechos após recorte: "
        f"{len(drenagem):,}"
    )


    # --------------------------------------------------------
    # REMOVER DUPLICIDADES
    # --------------------------------------------------------

    if "drn_pk" in drenagem.columns:

        drenagem = (

            drenagem

            .drop_duplicates(
                subset="drn_pk"
            )

            .copy()
        )


    # --------------------------------------------------------
    # CRS MÉTRICO
    # --------------------------------------------------------

    drenagem = drenagem.to_crs(
        epsg=CRS_METRICO
    )


    # --------------------------------------------------------
    # CAMPOS
    # --------------------------------------------------------

    drenagem[
        "codigo_ibge"
    ] = codigo


    drenagem[
        "drn_pk"
    ] = (

        drenagem[
            "drn_pk"
        ]

        .astype(
            "string"
        )
    )


    drenagem[
        "cotrecho"
    ] = (

        drenagem[
            "cotrecho"
        ]

        .astype(
            "string"
        )
    )


    drenagem[
        "cobacia"
    ] = (

        drenagem[
            "cobacia"
        ]

        .astype(
            "string"
        )
    )


    drenagem[
        "cocursodag"
    ] = (

        drenagem[
            "cocursodag"
        ]

        .astype(
            "string"
        )
    )


    drenagem[
        "nustrahler"
    ] = pd.to_numeric(

        drenagem[
            "nustrahler"
        ],

        errors="coerce",
    )


    drenagem[
        "nuareamont"
    ] = pd.to_numeric(

        drenagem[
            "nuareamont"
        ],

        errors="coerce",
    )


    drenagem[
        "nucomptrec"
    ] = pd.to_numeric(

        drenagem[
            "nucomptrec"
        ],

        errors="coerce",
    )


    # --------------------------------------------------------
    # SELEÇÃO FINAL
    # --------------------------------------------------------

    resultado = drenagem[
        [
            "codigo_ibge",
            "drn_pk",
            "cotrecho",
            "cobacia",
            "cocursodag",
            "noriocomp",
            "nustrahler",
            "nuareamont",
            "nucomptrec",
            "dsversao",
            "geometry",
        ]
    ].copy()


    resultado = resultado.rename(

        columns={

            "noriocomp":
                "nome_rio",

            "nustrahler":
                "ordem_strahler",

            "nuareamont":
                "area_montante_km2",

            "nucomptrec":
                "comprimento_trecho",

            "dsversao":
                "versao_bho",

            "geometry":
                "geom",
        }
    )


    resultado = resultado.set_geometry(
        "geom"
    )


    session_frames.append(
        resultado
    )


# ============================================================
# CONSOLIDAR
# ============================================================

if not session_frames:

    raise ValueError(
        "Nenhum trecho da BHO6 foi processado."
    )


final = pd.concat(

    session_frames,

    ignore_index=True,
)


final = gpd.GeoDataFrame(

    final,

    geometry="geom",

    crs="EPSG:5880",
)


print(
    "\nTotal de trechos a carregar: "
    f"{len(final):,}"
)


# ============================================================
# POSTGIS
# ============================================================

final.to_postgis(

    name="bho6_drenagem_alvo",

    schema="spatial",

    con=engine,

    if_exists="append",

    index=False,

    chunksize=2000,

    dtype={

        "geom":
            Geometry(
                geometry_type="MULTILINESTRING",
                srid=5880,
            )

    },
)


print("\n" + "=" * 72)
print("CARGA BHO6 CONCLUÍDA")
print("=" * 72)