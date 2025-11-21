# Technical Report — Final Project

**Course:** Cloud Computing
**Semester/YEAR:** 2nd Semester / 2025
**Team:** 
* Maria Eduarda Pompiani 
* Matheus Rodrigues Gomes 

---

## 1. Introduction

The analysis of urban environmental data is fundamental for planning smart cities, managing public health, and formulating sustainability policies. However, accessing unified, consistent, and automated climate and pollution data presents a significant challenge.

This project aimed to develop a "serverless" and cloud-native data pipeline to address this problem. The motivation was to create a low-cost, automated, and scalable solution capable of collecting, processing, and storing environmental data from all 27 Brazilian capitals.

The system uses GitHub Actions as its orchestrator and processing service, the OpenWeather API as the data source, and Azure Blob Storage as the storage destination, serving as a simplified "data lake" for future consumption in analytical tools.

## 2. Dataset

### Source and Description
The data is obtained from two OpenWeather API endpoints:
1.  **Current Weather (data/2.5/weather):** Provides current meteorological data, such as temperature, feels-like temperature, humidity, pressure, wind, and cloud cover.
2.  **Air Pollution (data/2.5/air_pollution):** Provides the Air Quality Index (AQI) and the concentration of pollutant components (CO, NO2, O3, SO2, PM2.5, PM10).

Data is collected for the 27 Brazilian capitals, whose coordinates (latitude and longitude) are defined in the `src/run_pipeline.py` script.

### Schema and Transformations
The raw data received from the API is in a nested JSON format. The `process_raw_data` function in the `src/run_pipeline.py` script performs the following transformations:
1.  **Normalization:** Uses `pandas.json_normalize` to flatten the JSON structures of the weather and pollution data.
2.  **Enrichment:** Adds crucial metadata for analysis, such as `city`, `collection_id` (a UUID for the run), and `collection_timestamp_utc`.
3.  **Renaming:** Columns are renamed to a clear and unified standard (e.g., `weather.main.temp` becomes `temperature_c`).
4.  **Selection:** Only columns relevant for the final analysis are retained.
5.  **Storage:** The resulting DataFrame is saved in CSV format.

The final CSV schema includes columns such as: `city`, `collection_timestamp_utc`, `temperature_c`, `feels_like_c`, `humidity_perc`, `aqi_index`, `pm2_5_ug_m3`, `pm10_ug_m3`, `no2_ug_m3`, `o3_ug_m3`, among others.

## 3. Solution Architecture

### Architecture Design
(See Mermaid Diagram in the "Solution Architecture" section of the README.md)

### Design Justifications

* **Azure Blob Storage (Storage):** Chosen for being a low-cost, highly durable, and scalable object storage service. It is ideal for a "data lake" pattern, where processed data (CSVs) can be stored and easily accessed by other tools, notably Power BI, which has native connectors.
* **GitHub Actions (Processing):** Although the requirement mentions Azure Functions or Container Apps, GitHub Actions was used as the processing and orchestration service. It fulfills the "processing service" requirement by being a "serverless" platform (from the user's perspective) that executes code (our Python script) in response to events (a schedule or manual trigger). The native integration with the repository (CI/CD) simplified development.
* **Bicep (IaC):** Used to define the infrastructure (Storage Account and Container). The Infrastructure as Code approach ensures the Azure environment is provisioned in a consistent, repeatable, and documented manner.
* **Docker (Local Development):** The use of `Dockerfile` and `docker-compose.yml` allows the developer to run the complete pipeline locally, ensuring that dependencies (Python, libraries) are identical to the execution environment, simulating isolation (although GHA uses VMs, not Docker, to run the script directly).
* **Read-Modify-Write Pattern:** The `run_pipeline.py` script implements an "append" logic by reading the existing CSV from the blob, concatenating the new data (via Pandas), and overwriting the file. This is essential for building the historical dataset.

### Security and Compliance
The solution's security is guaranteed by the following mechanisms:
1.  **Secret Management:** The OpenWeather API key and the Azure Storage Connection String are not in the code. They are stored as **GitHub Secrets** and injected into the pipeline's runtime environment as environment variables (`OPENWEATHER_API_KEY`, `AZURE_STORAGE_CONN_STR`).
2.  **Restricted Blob Access:** The Bicep infrastructure configures the `processed-data` container with public access disabled (`publicAccess: 'None'`). Access is only permitted via the Connection String.
3.  **Environment Files:** The `.env_example` guides local development, while `.env` files (containing local secrets) are ignored by Git (via `.gitignore`) and Docker (via `.dockerignore`).

## 4. Implementation

### Scripts and Pipelines Developed
* **`src/run_pipeline.py`:** The heart of the application. It orchestrates collection (iterating through cities), processing (calling `process_raw_data`), and storage (calling `upload_or_append_to_blob_csv`).
* **`iac/main.bicep`:** Declarative IaC script that defines the Storage Account and Container.
* **`.github/workflows/infra.yml`:** CI/CD pipeline for infrastructure. It is triggered by pushes to the `iac/` folder and executes the Bicep deploy.
* **`.github/workflows/pipeline.yml`:** CI/CD pipeline for data. It is triggered by a schedule (`cron: '0 9,21 * * *'`) or manually (`workflow_dispatch`). It installs dependencies and runs `run_pipeline.py`.

### Docker
* **`Dockerfile`:** Defines the execution image, starting from a `python:3.10-slim` base, copying and installing `requirements.txt`, and setting the default `CMD`.
* **`docker-compose.yml`:** Facilitates local execution by setting up the `data-pipeline` service and injecting the `.env` file.
* **`.dockerignore`:** Prevents unnecessary files (like `.git`, `.env`, `iac/`) from being copied into the Docker image, optimizing the build.

### Directory Structure
The torage Account Definition:**
```bicep
@description('The name of the Storage Account (must be globally unique).')
param storageAccountName string = 'st${uniqueString(resourceGroup().id)}'

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: storageAccountName
  location: location
  sku: {
    name: 'Standard_LRS' 
  }
  kind: 'StorageV2'
  properties: {
    accessTier: 'Hot'
    allowBlobPublicAccess: false
    supportsHttpsTrafficOnly: true
  }
}
```
### Directory Structure
The repository is organized as follows:
```text
.
├── .github/workflows/   # CI/CD Definitions (infra.yml, pipeline.yml)
├── iac/                 # Infrastructure as Code (main.bicep)
├── resources/images/    # Documentation assets and Dashboard screenshots
├── src/                 # Source code (run_pipeline.py)
├── .dockerignore        # Docker exclusion rules
├── .env_example         # Template for environment variables
├── .gitignore           # Git exclusion rules
├── BI-climate.pbix      # Power BI Project File
├── docker-compose.yml   # Local development orchestration
├── Dockerfile           # Container image definition
├── README.md            # Project documentation
├── requirements.txt     # Python dependencies
└── TECHNICAL_REPORT.md  # This report
```

## 5. Azure Infrastructure

### Provisioned Resources
The following resources are provisioned in Azure by the infrastructure pipeline:
* **Resource Group:** `rg-climate-project-final` (defined in the `infra.yml` workflow)
* **Storage Account:** `stclimaprojeto2025` (defined in the `infra.yml` workflow)
    * **SKU:** `Standard_LRS`
    * **Kind:** `StorageV2`
* **Blob Service Container:** `processed-data` (defined in `main.bicep`)

### IaC Used
The `iac/main.bicep` file defines the resources. Below are the key excerpts:

**Storage Account Definition:**
```bicep
@description('The name of the Storage Account (must be globally unique).')
param storageAccountName string = 'st${uniqueString(resourceGroup().id)}'

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: storageAccountName
  location: location
  sku: {
    name: 'Standard_LRS' 
  }
  kind: 'StorageV2'
  properties: {
    accessTier: 'Hot'
    allowBlobPublicAccess: false
    supportsHttpsTrafficOnly: true
  }
}
```

**Processed Data Container Definition:**
```bicep
resource processedContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  parent: blobService
  name: containerName
  properties: {
    publicAccess: 'None'
  }
}
```

## 6. CI/CD Pipeline

The project uses two GitHub Actions pipelines for complete automation (CI/CD and Data Orchestration).

### Infrastructure Pipeline (infra.yml)

* **Triggers:** `workflow_dispatch` (manual) and push to the `iac/**` folder.
* **Jobs:**
    * **Checkout Repository:** Downloads the code.
    * **Azure Login:** Authenticates to Azure using `AZURE_CREDENTIALS` (stored as a Secret).
    * **Deploy Bicep File:** Executes the deployment of `iac/main.bicep` using the defined parameters (Resource Group and Storage Account Name).

### Data Pipeline (pipeline.yml)

* **Triggers:** `workflow_dispatch` (manual) and `schedule` (cron: '0 9,21 * * *', twice daily).
* **Jobs:**
    * **Checkout Repository:** Downloads the code.
    * **Set up Python 3.10:** Configures the Python environment on the runner.
    * **Install Dependencies:** Installs the libraries from `requirements.txt`.
    * **Run Data Pipeline Script:** Executes `python src/run_pipeline.py`. This step injects the secrets (`OPENWEATHER_API_KEY`, `AZURE_STORAGE_CONN_STR`) as environment variables.

---

## 7. Observability and Performance

### Logs and Metrics

The solution's observability is primarily based on pipeline logs:

* **Application Logs:** The `src/run_pipeline.py` script uses Python's `logging` module to log the start of the pipeline, the processing of each city, and any potential errors or failures in collection/processing.
* **Execution Logs (CI/CD):** GitHub Actions captures all `stdout` and `stderr` from the script, allowing for post-execution analysis of any failures.
* **On the Azure side:** The Storage Account service provides native metrics (via Azure Monitor) on transactions (reads and writes), latency, and the volume of data stored.

### Test Results

The pipeline was tested locally (via `docker-compose`) and in the GitHub Actions environment (via `workflow_dispatch`) to validate:

* Connection to the OpenWeather API.
* Connection and authentication with Azure Blob Storage.
* Data processing and normalization logic.
* The "append" (Read-Modify-Write) logic in Blob Storage.

---

## 8. Results and Demonstration

The analytical interface was developed using **Microsoft Power BI**, connecting directly to the Azure Blob Storage container `processed-data`. The dashboard offers a comprehensive view of the climate and air quality across Brazil.

### 8.1. Analytical Interface

**Overview Dashboard:**
This screen serves as the central command hub. It features a geospatial map displaying the 27 capitals, with color-coded bubbles (Red/Blue) indicating temperature extremes ("Heat Islands"). Key KPIs at the top show the selected capital's average temperature and humidity, along with a qualitative Air Quality status.
*(See `resources/images/BI-Overview-climate-analysis-project-cloud-1.png` in the repository)*

**Thermal Analysis:**
This dashboard focuses on thermal comfort. It correlates the measured temperature (`temperature_c`) with the thermal sensation (`feels_like_c`) using scatter plots and line charts. It allows the identification of cities where high humidity exacerbates the feeling of heat, a critical metric for public health warnings.
*(See `resources/images/BI-Thermal-Analysis-climate-analysis-project-cloud-1.png` in the repository)*

**Humidity Monitoring:**
Dedicated to analyzing relative humidity. The visuals highlight critical levels (below 30% or above 80%). It includes a gauge chart for the current average and a bar chart showing the daily progression of humidity versus temperature, aiding in the prediction of dry weather respiratory risks.
*(See `resources/images/BI-Humidity-Monitoring-climate-analysis-project-cloud-1.png` in the repository)*

**Wind Dynamics:**
This view analyzes wind patterns using radar charts (Wind Rose concept) and line graphs. It visualizes wind speed (`wind_speed_ms`) and direction, providing insights into atmospheric circulation and potential pollutant dispersion patterns.
*(See `resources/images/BI-Wind-Dinamics-climate-analysis-project-cloud-1.png` in the repository)*

**Air Quality:**
A critical environmental view that breaks down the Air Quality Index (AQI). Pie and area charts display the concentration of specific pollutants such as Particulate Matter (PM2.5, PM10), Nitrogen Dioxide (NO2), and Ozone (O3). This allows for a detailed assessment of pollution sources and trends over time.
*(See `resources/images/BI-Air-Quality-climate-analysis-project-cloud-1.png` in the repository)*

### 8.2. Metrics Obtained
During the validation period, the system successfully processed data for all 27 capitals. Key metrics observed in the dashboard examples include:
* **Average Temperature:** Ranges observed around ~25°C in the overview.
* **Humidity Levels:** High variation, with averages around 72-75% in coastal areas.
* **Wind Speeds:** Averages around 3-4 m/s.
* **Pollution:** Detailed breakdown of PM2.5 and Ozone levels, crucial for urban environmental compliance.

### 8.3. Solution Limitations
* **"Append" Performance:** The `upload_or_append_to_blob_csv` logic implements a "Read-Modify-Write" pattern. As the CSV files grow (thousands of rows), the transaction cost (data egress and write) and execution time will increase linearly.
* **Processing Service:** Using GitHub Actions as a processing service is convenient for this academic scope but is less integrated into the Azure ecosystem than an Azure Function.
* **Data Source Limits:** The free tier of the OpenWeather API has call limits which restricts the frequency of updates (currently set to twice daily).

## 9. Conclusion and Future Work

### Key Learnings

The project provided practical application of fundamental cloud computing concepts, including:

* **Infrastructure as Code (IaC):** Using Bicep for declarative resource provisioning.
* **Automation (CI/CD):** Configuring GitHub Actions pipelines for infrastructure deployment and data orchestration.
* **PaaS Services:** Using Azure Blob Storage as a managed storage solution.
* **Containerized Development:** Applying Docker and Docker Compose to ensure portability and reproducibility of the development environment.
* **Security:** Managing secrets and configuring secure access to resources.

### Possible Improvements and Scalability

To evolve the solution, the following improvements are suggested:

* **Migrate Processing to Azure:** Replace the script's execution in GitHub Actions with an Azure Function (Consumption Plan) or Azure Container App. This would bring the processing into the Azure ecosystem, facilitating monitoring (Application Insights) and identity management (Managed Identity) instead of Connection Strings.
* **Optimize Storage:** Replace the "Read-Modify-Write" pattern on CSVs with:
    * **Append Blobs:** A blob type optimized for "append" operations.
    * **Azure Data Lake Storage Gen2:** Store the data in Parquet format instead of CSV, which offers better compression and read performance for Power BI.
    * **Azure SQL Database:** Insert records directly into a relational database, which eliminates the "append" problem and improves query performance.
* **Advanced Monitoring:** Integrate the Python script with Azure Application Insights for advanced telemetry, rather than relying solely on text logs.