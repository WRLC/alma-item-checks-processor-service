"""Institution CRUD API endpoints"""

import json
import logging
from typing import Any

import azure.functions as func

from alma_item_checks_processor_service.database import SessionMaker
from alma_item_checks_processor_service.repos.institution_repo import (
    InstitutionRepository,
)
from alma_item_checks_processor_service.models.institution import Institution

bp: func.Blueprint = func.Blueprint()


def institution_to_dict(institution: Institution) -> dict[str, Any]:
    """Convert Institution model to dictionary for JSON serialization"""
    return {
        "id": institution.id,
        "name": institution.name,
        "code": institution.code,
        "api_key": institution.api_key,
        "duplicate_report_path": institution.duplicate_report_path,
    }


# noinspection PyUnusedLocal
@bp.function_name("get_institutions")
@bp.route(route="institutions", methods=["GET"], auth_level=func.AuthLevel.FUNCTION)
def get_institutions(req: func.HttpRequest) -> func.HttpResponse:
    """Get all institutions"""
    try:
        with SessionMaker() as session:
            repo = InstitutionRepository(session)
            institutions = repo.get_all_institutions()

            return func.HttpResponse(
                json.dumps([institution_to_dict(inst) for inst in institutions]),
                status_code=200,
                mimetype="application/json",
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type",
                },
            )
    except Exception as e:
        logging.error(f"Error getting institutions: {e}")
        return func.HttpResponse(
            json.dumps({"error": "Internal server error"}),
            status_code=500,
            mimetype="application/json",
        )


@bp.function_name("get_institution")
@bp.route(
    route="institutions/{id:int}", methods=["GET"], auth_level=func.AuthLevel.FUNCTION
)
def get_institution(req: func.HttpRequest) -> func.HttpResponse:
    """Get institution by ID"""
    try:
        institution_id = int(req.route_params.get("id"))

        with SessionMaker() as session:
            repo = InstitutionRepository(session)
            institution = repo.get_institution_by_id(institution_id)

            if not institution:
                return func.HttpResponse(
                    json.dumps({"error": "Institution not found"}),
                    status_code=404,
                    mimetype="application/json",
                )

            return func.HttpResponse(
                json.dumps(institution_to_dict(institution)),
                status_code=200,
                mimetype="application/json",
            )
    except ValueError:
        return func.HttpResponse(
            json.dumps({"error": "Invalid institution ID"}),
            status_code=400,
            mimetype="application/json",
        )
    except Exception as e:
        logging.error(f"Error getting institution: {e}")
        return func.HttpResponse(
            json.dumps({"error": "Internal server error"}),
            status_code=500,
            mimetype="application/json",
        )


@bp.function_name("get_institution_api_key")
@bp.route(
    route="institutions/{id:int}/api-key",
    methods=["GET"],
    auth_level=func.AuthLevel.FUNCTION,
)
def get_institution_api_key(req: func.HttpRequest) -> func.HttpResponse:
    """Get API key for institution by ID - for downstream services"""
    try:
        institution_id = int(req.route_params.get("id"))

        with SessionMaker() as session:
            repo = InstitutionRepository(session)
            institution = repo.get_institution_by_id(institution_id)

            if not institution:
                return func.HttpResponse(
                    json.dumps({"error": "Institution not found"}),
                    status_code=404,
                    mimetype="application/json",
                )

            return func.HttpResponse(
                json.dumps({"api_key": institution.api_key}),
                status_code=200,
                mimetype="application/json",
            )
    except ValueError:
        return func.HttpResponse(
            json.dumps({"error": "Invalid institution ID"}),
            status_code=400,
            mimetype="application/json",
        )
    except Exception as e:
        logging.error(f"Error getting institution API key: {e}")
        return func.HttpResponse(
            json.dumps({"error": "Internal server error"}),
            status_code=500,
            mimetype="application/json",
        )


@bp.function_name("create_institution")
@bp.route(route="institutions", methods=["POST"], auth_level=func.AuthLevel.FUNCTION)
def create_institution(req: func.HttpRequest) -> func.HttpResponse:
    """Create a new institution"""
    try:
        req_body = req.get_json()

        if not req_body:
            return func.HttpResponse(
                json.dumps({"error": "Request body is required"}),
                status_code=400,
                mimetype="application/json",
            )

        required_fields = ["name", "code", "api_key"]
        missing_fields = [field for field in required_fields if field not in req_body]

        if missing_fields:
            return func.HttpResponse(
                json.dumps(
                    {"error": f"Missing required fields: {', '.join(missing_fields)}"}
                ),
                status_code=400,
                mimetype="application/json",
            )

        with SessionMaker() as session:
            repo = InstitutionRepository(session)
            institution = repo.create_institution(
                name=req_body["name"],
                code=req_body["code"],
                api_key=req_body["api_key"],
                duplicate_report_path=req_body.get("duplicate_report_path"),
            )

            if not institution:
                return func.HttpResponse(
                    json.dumps({"error": "Failed to create institution"}),
                    status_code=500,
                    mimetype="application/json",
                )

            return func.HttpResponse(
                json.dumps(institution_to_dict(institution)),
                status_code=201,
                mimetype="application/json",
            )
    except Exception as e:
        logging.error(f"Error creating institution: {e}")
        return func.HttpResponse(
            json.dumps({"error": "Internal server error"}),
            status_code=500,
            mimetype="application/json",
        )


@bp.function_name("update_institution")
@bp.route(
    route="institutions/{id:int}", methods=["PUT"], auth_level=func.AuthLevel.FUNCTION
)
def update_institution(req: func.HttpRequest) -> func.HttpResponse:
    """Update an existing institution"""
    try:
        institution_id = int(req.route_params.get("id"))
        req_body = req.get_json()

        if not req_body:
            return func.HttpResponse(
                json.dumps({"error": "Request body is required"}),
                status_code=400,
                mimetype="application/json",
            )

        allowed_fields = ["name", "code", "api_key", "duplicate_report_path"]
        updates = {k: v for k, v in req_body.items() if k in allowed_fields}

        if not updates:
            return func.HttpResponse(
                json.dumps({"error": "No valid fields to update"}),
                status_code=400,
                mimetype="application/json",
            )

        with SessionMaker() as session:
            repo = InstitutionRepository(session)
            institution = repo.update_institution(institution_id, **updates)

            if not institution:
                return func.HttpResponse(
                    json.dumps({"error": "Institution not found or update failed"}),
                    status_code=404,
                    mimetype="application/json",
                )

            return func.HttpResponse(
                json.dumps(institution_to_dict(institution)),
                status_code=200,
                mimetype="application/json",
            )
    except ValueError:
        return func.HttpResponse(
            json.dumps({"error": "Invalid institution ID"}),
            status_code=400,
            mimetype="application/json",
        )
    except Exception as e:
        logging.error(f"Error updating institution: {e}")
        return func.HttpResponse(
            json.dumps({"error": "Internal server error"}),
            status_code=500,
            mimetype="application/json",
        )


@bp.function_name("delete_institution")
@bp.route(
    route="institutions/{id:int}",
    methods=["DELETE"],
    auth_level=func.AuthLevel.FUNCTION,
)
def delete_institution(req: func.HttpRequest) -> func.HttpResponse:
    """Delete an institution"""
    try:
        institution_id = int(req.route_params.get("id"))

        with SessionMaker() as session:
            repo = InstitutionRepository(session)
            success = repo.delete_institution(institution_id)

            if not success:
                return func.HttpResponse(
                    json.dumps({"error": "Institution not found"}),
                    status_code=404,
                    mimetype="application/json",
                )

            return func.HttpResponse(
                json.dumps({"message": "Institution deleted successfully"}),
                status_code=200,
                mimetype="application/json",
            )
    except ValueError:
        return func.HttpResponse(
            json.dumps({"error": "Invalid institution ID"}),
            status_code=400,
            mimetype="application/json",
        )
    except Exception as e:
        logging.error(f"Error deleting institution: {e}")
        return func.HttpResponse(
            json.dumps({"error": "Internal server error"}),
            status_code=500,
            mimetype="application/json",
        )
