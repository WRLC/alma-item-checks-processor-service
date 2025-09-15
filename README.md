# Alma Item Checks Processor Service

Processor service for WRLC's Alma Item Checks application

Processes item data from the Ex Libris Alma library management system, using event-driven architecture to retrieve item data by barcode and perform various data integrity checks and correct data errors where possible. Results are stored for further action by downstream services, including Alma API item updates and staff email notifications.
## Key Dependencies

- **Azure Functions v4**: Serverless compute platform with extension bundle
- **Azure Storage**: Blob storage, Queues, and Tables for data persistence and workflow orchestration
- **MySQL**: Relational database system
- **SQLAlchemy 2.0+**: Database ORM with session-per-operation pattern
- **PyMySQL**: MySQL database connector
- **Alembic**: Database migration management
- **wrlc_alma_api_client**: Custom WRLC client library for Alma API integration
- **wrlc_azure_storage_service**: Custom WRLC client for Azure Storage operations

## Processing Workflow

1. Queue message triggers `process_item_data` function with institution code, barcode, and process type
2. `ProcessorService` retrieves item data from Alma API using institution's API key
3. Institution-specific processor (SCF or IZ) determines if item should be processed based on business rules
4. If processing is required, appropriate processor handles the specific workflow (e.g., missing row/tray data, provenance issues)
5. Results are stored in blob containers and/or Azure Tables for downstream processing

## Environment Configuration

Required environment variables:
- `AzureWebJobsStorage`: Azure Storage connection string
- `SQLALCHEMY_CONNECTION_STRING`: Database connection string
- `FETCH_QUEUE`: Input queue name (default: "fetch-item-queue")
- `SCF_NO_X_QUEUE`, `SCF_NO_ROW_TRAY_QUEUE`, `SCF_WD_QUEUE`: Output queues for different SCF processes
- `SCF_NO_X_CONTAINER`, `SCF_NO_ROW_TRAY_CONTAINER`, `SCF_WD_CONTAINER`: Blob containers for processed data
- `SCF_NO_ROW_TRAY_STAGE_TABLE`, `SCF_NO_ROW_TRAY_REPORT_TABLE`: Azure Table storage names
- `API_CLIENT_TIMEOUT`: Alma API timeout in seconds (default: 90)

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

## Infrastructure

The project includes Terraform configuration (`terraform/`) for Azure resource provisioning including Function Apps, MySQL Flexible Server databases, and Application Insights for production and a 'stage' slot. Requires shared resources provisioned by [alma-item-checks-infrastructure-shared](https://github.com/WRLC/alma-item-checks-infrastructure-shared).

The Terraform configuration automatically sets the environment variables listed above under "Environment Configuration."

## Disclaimer

This application integrates with the [Alma library management system](https://exlibrisgroup.com/products/alma-library-services-platform/) but is not created by, affiliated with, or endorsed by [Ex Libris Group](https://exlibrisgroup.com/) or [Clarivate](https://clarivate.com/) in any way.
