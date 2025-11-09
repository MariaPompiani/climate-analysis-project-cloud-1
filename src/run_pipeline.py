import os
import requests
import pandas as pd
import logging
import traceback
import uuid
import io
from datetime import datetime, timezone
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient

# --- Config ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Cidades (Todas as 27 capitais do Brasil)
CITIES = [
    ("Aracaju", -10.9167, -37.0667),
    ("Belem", -1.4558, -48.5044),
    ("Belo Horizonte", -19.9167, -43.9333),
    ("Boa Vista", 2.8197, -60.6733),
    ("Brasilia", -15.7942, -47.8825),
    ("Campo Grande", -20.4667, -54.6167),
    ("Cuiaba", -15.5969, -56.0969),
    ("Curitiba", -25.4284, -49.2733),
    ("Florianopolis", -27.5969, -48.5494),
    ("Fortaleza", -3.7172, -38.5431),
    ("Goiania", -16.6833, -49.25),
    ("Joao Pessoa", -7.115, -34.8631),
    ("Macapa", 0.0389, -51.0664),
    ("Maceio", -9.6658, -35.7353),
    ("Manaus", -3.1190, -60.0217),
    ("Natal", -5.7944, -35.2089),
    ("Palmas", -10.1833, -48.3333),
    ("Porto Alegre", -30.0331, -51.23),
    ("Porto Velho", -8.7619, -63.9039),
    ("Recife", -8.0539, -34.8808),
    ("Rio Branco", -9.9747, -67.81),
    ("Rio de Janeiro", -22.9068, -43.1729),
    ("Salvador", -12.9777, -38.5016),
    ("Sao Luis", -2.5307, -44.3068),
    ("Sao Paulo", -23.5505, -46.6333),
    ("Teresina", -5.0892, -42.8019),
    ("Vitoria", -20.3194, -40.3378)
]

# Segredos (lidos das variáveis de ambiente)
try:
    API_KEY = os.environ["OPENWEATHER_API_KEY"]
    STORAGE_CONN_STR = os.environ["AZURE_STORAGE_CONN_STR"]
except KeyError as e:
    logging.error(f"Erro: Variável de ambiente {e} não definida. "
                  "Se rodando localmente, verifique seu arquivo .env")
    exit(1)


# Contêiner
PROCESSED_CONTAINER = "processed-data"

# URLs
BASE_URL_WEATHER = "https://api.openweathermap.org/data/2.5/weather"
BASE_URL_AIRPOLLUTION = "https://api.openweathermap.org/data/2.5/air_pollution"

# --- Fim Config ---


def fetch_api_data(url, params):
    """Função genérica para chamar uma API."""
    try:
        response = requests.get(url, params=params)
        response.raise_for_status() # Lança erro para status HTTP 4xx/5xx
        return response.json()
    except requests.RequestException as e:
        logging.error(f"Erro ao chamar API {url} com params {params}: {e}")
        return None

def fetch_city_data(city_name, lat, lon, api_key):
    """Coleta dados de clima e poluição para uma cidade."""
    
    # Parâmetros comuns
    common_params = {'lat': lat, 'lon': lon, 'appid': api_key}
    
    # 1. Coletar dados de Clima
    weather_params = {**common_params, 'units': 'metric', 'lang': 'pt_br'}
    weather_data = fetch_api_data(BASE_URL_WEATHER, weather_params)

    # 2. Coletar dados de Poluição do Ar
    air_pollution_data = fetch_api_data(BASE_URL_AIRPOLLUTION, common_params)

    if weather_data and air_pollution_data:
        return {
            'weather_data': weather_data,
            'air_pollution_data': air_pollution_data
        }
    return None

#
# ESTA É A SUA FUNÇÃO DE PROCESSAMENTO (COPIADA E COLADA)
#
def process_raw_data(raw_data, in_blob_name):
    """
    Esta função é a lógica do seu 'DataProcessor' original.
    Ela recebe o JSON bruto e retorna um DataFrame do Pandas.
    """
    try:
        df_weather = pd.json_normalize(
            raw_data['weather_data'],
            record_path=['weather'],
            meta=[
                ['main', 'temp'],
                ['main', 'feels_like'],
                ['main', 'humidity'],
                ['main', 'pressure'],
                ['wind', 'speed'],
                ['wind', 'deg'],
                ['wind', 'gust'],
                ['clouds', 'all'],
                ['visibility'],
                ['sys', 'sunrise'],
                ['sys', 'sunset']
            ],
            meta_prefix='weather.',
            errors='ignore'
        )
        
        if 'rain' in raw_data['weather_data'] and '1h' in raw_data['weather_data']['rain']:
            df_weather['rain_1h_mm'] = raw_data['weather_data']['rain']['1h']
        else:
            df_weather['rain_1h_mm'] = pd.NA

        df_air = pd.json_normalize(
            raw_data['air_pollution_data'],
            record_path=['list'],
            meta_prefix='air.',
            errors='ignore'
        )

        df_combined = pd.concat([df_weather.reset_index(drop=True), df_air.reset_index(drop=True)], axis=1)

        df_combined['city'] = raw_data['app_metadata']['city_name']
        df_combined['collection_id'] = raw_data['app_metadata']['collection_id']
        df_combined['collection_timestamp_utc'] = raw_data['app_metadata']['collection_timestamp_utc']
        df_combined['raw_blob_name'] = in_blob_name # Apenas uma referência de nome

        df_final = df_combined.rename(columns={
            'weather.main.temp': 'temperature_c',
            'weather.main.feels_like': 'feels_like_c',
            'weather.main.humidity': 'humidity_perc',
            'weather.main.pressure': 'pressure_hpa',
            'weather.wind.speed': 'wind_speed_ms',
            'weather.wind.deg': 'wind_direction_deg',
            'weather.wind.gust': 'wind_gust_ms',
            'weather.clouds.all': 'clouds_perc',
            'weather.visibility': 'visibility_m',
            'weather.sys.sunrise': 'sunrise_timestamp',
            'weather.sys.sunset': 'sunset_timestamp',
            'description': 'weather_condition',
            'icon': 'weather_icon',
            'main.aqi': 'aqi_index',
            'components.pm2_5': 'pm2_5_ug_m3',
            'components.pm10': 'pm10_ug_m3',
            'components.no2': 'no2_ug_m3',
            'components.o3': 'o3_ug_m3',
            'components.so2': 'so2_ug_m3',
            'components.co': 'co_ug_m3'
        })
        
        final_columns = [
            'city', 'collection_timestamp_utc', 'temperature_c', 'feels_like_c',
            'humidity_perc', 'pressure_hpa', 'wind_speed_ms', 'wind_direction_deg',
            'wind_gust_ms', 'rain_1h_mm', 'clouds_perc', 'visibility_m',
            'sunrise_timestamp', 'sunset_timestamp', 'weather_condition', 'weather_icon',
            'aqi_index', 'pm2_5_ug_m3', 'pm10_ug_m3', 'no2_ug_m3', 'o3_ug_m3',
            'collection_id', 'raw_blob_name'
        ]
        
        # Filtra para manter apenas colunas que existem no df_final
        df_final_filtered = df_final[[col for col in final_columns if col in df_final.columns]]
        return df_final_filtered

    except Exception as e:
        logging.error(f"Erro ao processar dados: {e}\nTrace: {traceback.format_exc()}")
        return None
#
# FIM DA SUA FUNÇÃO
#

def upload_or_append_to_blob_csv(df_new, conn_str, container_name, blob_name):
    """
    Faz upload ou "append" de um DataFrame a um CSV no Blob Storage.
    Implementa o padrão Read-Modify-Write.
    """
    try:
        blob_service_client = BlobServiceClient.from_connection_string(conn_str)
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)

        df_combined = df_new

        # 1. Tenta Ler (Read)
        if blob_client.exists():
            logging.info(f"Arquivo {blob_name} encontrado. Baixando para fazer append...")
            try:
                # Baixa o CSV existente para um stream em memória
                downloader = blob_client.download_blob()
                stream = io.BytesIO(downloader.readall())
                
                # Lê o CSV antigo
                df_old = pd.read_csv(stream)
                
                # 2. Modifica (Modify) - Junta o antigo com o novo
                logging.info(f"Juntando {len(df_old)} registros antigos com {len(df_new)} novos...")
                df_combined = pd.concat([df_old, df_new], ignore_index=True)
                
            except Exception as e:
                logging.warning(f"Falha ao ler ou processar o blob {blob_name}. "
                                f"O arquivo será sobrescrito APENAS com os dados novos. Erro: {e}")
                # Se falhar (ex: CSV corrompido), apenas usa o df_new
                df_combined = df_new
        else:
            logging.info(f"Arquivo {blob_name} não encontrado. Criando novo arquivo...")

        # Converte o DataFrame (novo ou combinado) para CSV em memória
        csv_data = df_combined.to_csv(index=False, encoding='utf-8')
        
        # 3. Escreve (Write)
        logging.info(f"Fazendo upload de {len(df_combined)} registros para {container_name}/{blob_name}...")
        blob_client.upload_blob(csv_data, blob_type="BlockBlob", overwrite=True)
        logging.info(f"Upload para {blob_name} concluído com sucesso.")
        
    except Exception as e:
        logging.error(f"Erro ao fazer upload/append para o Blob Storage: {e}\nTrace: {traceback.format_exc()}")

def main():
    """Função principal para orquestrar o pipeline."""
    logging.info("Iniciando pipeline de coleta de dados climáticos...")
    
    collection_id = str(uuid.uuid4())
    collection_timestamp_utc = datetime.now(timezone.utc).isoformat()
    
    for city_name, lat, lon in CITIES:
        logging.info(f"--- Processando: {city_name} ---")
        
        # 1. Coleta
        raw_data_payload = fetch_city_data(city_name, lat, lon, API_KEY)
        
        if raw_data_payload:
            # Adiciona metadados para sua função de processamento
            raw_data_payload['app_metadata'] = {
                'city_name': city_name,
                'collection_id': collection_id,
                'collection_timestamp_utc': collection_timestamp_utc
            }
            
            # 2. Processamento (usando sua função)
            # O nome do "raw_blob_name" é simbólico aqui
            raw_blob_ref_name = f"{collection_id}_{city_name.lower().replace(' ','_')}.json"
            df_processed = process_raw_data(raw_data_payload, in_blob_name=raw_blob_ref_name)
            
            if df_processed is not None and not df_processed.empty:
                # 3. Armazenamento (Upload/Append)
                
                # Define o nome do blob de saída, ex: "sao_paulo.csv"
                processed_blob_name = f"{city_name.lower().replace(' ', '_').replace('ã', 'a').replace('é', 'e').replace('á', 'a').replace('ç', 'c')}.csv"
                
                # Chama a nova função de upload que faz o append
                upload_or_append_to_blob_csv(
                    df_processed, 
                    STORAGE_CONN_STR, 
                    PROCESSED_CONTAINER, 
                    processed_blob_name
                )
            else:
                logging.warning(f"Falha ao processar dados para {city_name}. DataFrame vazio.")
        else:
            logging.warning(f"Falha ao coletar dados para {city_name}.")

    logging.info("--- Pipeline concluído ---")

if __name__ == "__main__":
    # Se rodando localmente (não no GitHub Actions), carrega variáveis do .env
    if os.getenv("GITHUB_ACTIONS") != "true":
        try:
            from dotenv import load_dotenv
            # O __file__ se refere a src/run_pipeline.py, então .. volta para a raiz
            dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
            if os.path.exists(dotenv_path):
                load_dotenv(dotenv_path=dotenv_path)
                logging.info("Variáveis de ambiente carregadas do .env para teste local.")
            else:
                logging.warning("Arquivo .env não encontrado na raiz do projeto. "
                                "Assumindo que as variáveis de ambiente estão definidas manualmente.")
            
            # Recarrega as variáveis após o load_dotenv
            API_KEY = os.environ["OPENWEATHER_API_KEY"]
            STORAGE_CONN_STR = os.environ["AZURE_STORAGE_CONN_STR"]
        except ImportError:
            logging.warning("Biblioteca python-dotenv não encontrada. "
                            "Assumindo que as variáveis de ambiente estão definidas manualmente.")
        except KeyError as e:
            logging.error(f"Erro ao carregar do .env: Variável {e} não definida.")
            exit(1)

    main()