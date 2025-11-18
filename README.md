# Climate Data Analysis System - Brazilian Capitals

This project, developed for the Cloud Computing course, implements an automated data pipeline to collect, process, and store climate and air pollution data from the 27 capital cities of Brazil, using the OpenWeather API and Microsoft Azure services.

## Team

* **Student:** Maria Eduarda Pompiani
* **Student:** Matheus Rodrigues Gomes
* **Email:** maria.esapc@puccampinas.edu.br
* **Email:** 

## General Description

The objective of this system is to create a unified historical dataset of environmental conditions in Brazil's major cities. The pipeline runs automatically twice a day, collecting meteorological data (such as temperature, humidity, wind) and air quality data (such as PM2.5, NO2, O3 levels).

The data is processed and stored in **Azure Blob Storage**, ready to be consumed by visualization tools like Power BI for trend analysis, correlation studies, and generating insights into urban climate across the country.

## Dataset

* **Data Source:** [OpenWeather API](https://openweathermap.org/api), utilizing the "Current Weather Data" and "Air Pollution API" endpoints.
* **Expected Data Volume:** The pipeline is scheduled to run twice daily (09:00 and 21:00 UTC). In each run, 27 records (one for each capital) are collected and processed. The data is appended to individual CSV files per city, allowing the dataset to grow over time.
* **Licensing:** Use of the data is subject to the OpenWeather API's terms of service.

## Solution Architecture

The diagram below illustrates the system architecture, from the data pipeline orchestration and execution to storage in Azure and the future visualization layer.

```mermaid
graph TD
    subgraph "Local Development"
        A[Developer] -- 'docker-compose up' --> B(Docker Container);
        B -- reads .env --> C[src/run_pipeline.py];
    end

    subgraph "CI/CD - GitHub Actions"
        G(Push to 'main' - iac/ folder) --> H[Workflow 'infra.yml'];
        H -- Bicep Deploy --> I[Provision Azure Infra];

        J(Schedule 9h/21h UTC) --> K[Workflow 'pipeline.yml'];
        L(Manual Trigger) --> K;
    end

    subgraph "Execution (GitHub Runner)"
        K --> M(Setup Python & Dependencies);
        M -- 'python src/run_pipeline.py' --> N(Run Script);
    end

    subgraph "Azure Platform"
        I --> O(Resource Group: rg-climate-project-final);
        O --> P[Storage Account: stclimaprojeto2025];
        P --> Q(Container: processed-data);
    end

    subgraph "Data Flow"
         N -- API KEY --> R(OpenWeather API);
         R -- JSON Data --> N;
         N -- Process (Pandas) --> S(DataFrame);
         S -- Conn String (Secrets) --> Q;
         Q -- (Read-Modify-Write) --> Q(CSVs per city);
    end

    subgraph "Visualization (Pending)"
        Q -- Power BI Connector --> T[Power BI Dashboard];
    end
```

## Demonstration
(This section will be filled in after the dashboard is created)

Dashboard Screenshots (Power BI):

(Insert image of the analytical dashboard)

(Insert image with details of a specific city)

Link to Demo Video:

(Insert link from YouTube, Stream, etc.)

## References
APIs:
- OpenWeather API: https://openweathermap.org/api

Azure Services:
- Azure Blob Storage Documentation: https://docs.microsoft.com/en-us/azure/storage/blobs/
- Azure Bicep Documentation: https://docs.microsoft.com/en-us/azure/bicep/

Tools:
- GitHub Actions: https://docs.github.com/en/actions
- Pandas: https://pandas.pydata.org/
