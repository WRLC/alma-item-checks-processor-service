# alma-item-checks-processor-service

Python-based Azure Function microservice that processes library item data from the Alma API. Part of the Alma Item Checks application.

The service validates and processes items based on institution-specific rules, handling different workflows for SCF (Shared Collection Facility) and partner IZ (Institution Zone) items.

## Architecture

The application follows a layered architecture with a processor pattern:

- **Function App** (`function_app.py`): Main Azure Functions entry point that registers blueprints
- **Blueprints** (`blueprints/`): Azure Function triggers and HTTP endpoints
  - `bp_processor.py`: Queue-triggered function `process_item_data` that processes barcode messages
- **Services** (`services/`): Business logic layer with processor pattern
  - `processor_service.py`: Main orchestrator that coordinates item retrieval, validation, and processing
  - `base_processor.py`: Abstract base class defining common processing logic and utilities
  - `scf_item_processor.py`: SCF-specific item processing rules and workflows
  - `iz_item_processor.py`: IZ-specific item processing rules and workflows  
  - `institution_service.py`: Institution data access operations
- **Models** (`models/`): SQLAlchemy database models
  - `institution.py`: Institution entity with API keys and institutional codes
- **Repositories** (`repos/`): Data access layer
  - `institution_repo.py`: Institution database operations
- **Config** (`config.py`): Environment variables and business logic constants including provenance data, excluded notes, and location mappings

## Key Dependencies

- **Azure Functions v4**: Serverless compute platform with extension bundle
- **MySQL**: Relational database system
- **SQLAlchemy 2.0+**: Database ORM with session-per-operation pattern
- **Azure Storage**: Blob storage, Queues, and Tables for data persistence and workflow orchestration
- **wrlc_alma_api_client**: Custom WRLC client library for Alma API integration
- **wrlc_azure_storage_service**: Custom WRLC client for Azure Storage operations
- **PyMySQL**: MySQL database connector
- **Alembic**: Database migration management

## Local Development Setup

The project includes Azurite configuration for local Azure Storage emulation. (Requires [Azurite](https://github.com/Azure/Azurite).) The `azurite-data/` directory contains local storage state and should not be committed to version control.

To start local function, in one terminal window/tab run:

```shell
azurite -s -d azurite-debug.log -l azurite-data
```

In another terminal window/tab run:

```shell
func start
```

## Environment Configuration

Required environment variables:
- `AzureWebJobsStorage`: Azure Storage connection string
- `SQLALCHEMY_CONNECTION_STRING`: Database connection string
- `FETCH_QUEUE`: Input queue name (default: "fetch-item-queue")
- `SCF_NO_X_QUEUE`, `SCF_NO_ROW_TRAY_QUEUE`, `SCF_WD_QUEUE`: Output queues for different SCF processes
- `SCF_NO_X_CONTAINER`, `SCF_NO_ROW_TRAY_CONTAINER`, `SCF_WD_CONTAINER`: Blob containers for processed data
- `SCF_NO_ROW_TRAY_STAGE_TABLE`, `SCF_NO_ROW_TRAY_REPORT_TABLE`: Azure Table storage names
- `API_CLIENT_TIMEOUT`: Alma API timeout in seconds (default: 90)

## Processing Workflow

1. Queue message triggers `process_item_data` function with institution code, barcode, and process type
2. `ProcessorService` retrieves item data from Alma API using institution's API key
3. Institution-specific processor (SCF or IZ) determines if item should be processed based on business rules
4. If processing is required, appropriate processor handles the specific workflow (e.g., missing row/tray data, provenance issues)
5. Results are stored in blob containers and/or Azure Tables for downstream processing

## Business Logic Patterns

- **Processor Pattern**: `BaseItemProcessor` provides common functionality, with `SCFItemProcessor` and `IZItemProcessor` implementing institution-specific rules
- **Session Management**: SQLAlchemy sessions use context managers for proper resource cleanup
- **Retry Logic**: Alma API calls include exponential backoff retry logic (3 attempts)
- **Configuration-Driven**: Business rules (provenance mappings, excluded notes, skip locations) are centralized in `config.py`

## Infrastructure

The project includes Terraform configuration (`terraform/`) for Azure resource provisioning including Function Apps, Storage Accounts, and Application Insights.