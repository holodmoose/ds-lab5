from fastapi import Depends, FastAPI, HTTPException, Header, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import os
import datetime
import uuid
import sys
import inspect
import logging

logger = logging.getLogger(f"uvicorn.{__name__}")


currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)

from common import *
from services import *
from auth_service import AuthService
from jwks_service import JWKSService
from jwt_service import JWTService

FLIGHTS_SERVICE_URL = os.getenv("FLIGHTS_SERVICE_URL")
TICKETS_SERVICE_URL = os.getenv("TICKETS_SERVICE_URL")
PRIVILEGES_SERVICE_URL = os.getenv("PRIVILEGES_SERVICE_URL")
IDP_ENDPOINT = os.getenv("IDP_ENDPOINT")
AUTH_CLIENT_ID = os.getenv("AUTH_CLIENT_ID")
AUTH_CLIENT_SECRET = os.getenv("AUTH_CLIENT_SECRET")
JWKS_ENDPOINT = os.getenv("JWKS_ENDPOINT")

if FLIGHTS_SERVICE_URL is None:
    raise RuntimeError("missing FLIGHTS_SERVICE_URL")
if TICKETS_SERVICE_URL is None:
    raise RuntimeError("missing TICKETS_SERVICE_URL")
if PRIVILEGES_SERVICE_URL is None:
    raise RuntimeError("missing PRIVILEGES_SERVICE_URL")

flights_service = FlightsService(FLIGHTS_SERVICE_URL)
tickets_service = TicketsService(TICKETS_SERVICE_URL)
privileges_service = PrivilegesService(PRIVILEGES_SERVICE_URL)
auth_service = AuthService(IDP_ENDPOINT, AUTH_CLIENT_ID, AUTH_CLIENT_SECRET)
jwks_service = JWKSService(JWKS_ENDPOINT)
jwt_service = JWTService(jwks_service)

jwks_service.get_jwks()

app = FastAPI(title="App API", root_path="/api/v1")
print("HELLO")
logger.info("HELLOWOEOAWEOA")


def get_current_user(req: Request) -> UserInfo:
    print("checking authorization")
    authorization = req.headers.get("Authorization")
    if not authorization:
        logger.error("Missing Authorization header")
        raise HTTPException(status_code=401, detail="Authorization header missing")

    print(f"got authorization {authorization}")

    # Extract token from "Bearer <token>"
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise ValueError("Invalid authorization scheme")
    except ValueError:
        logger.error("Invalid Authorization header format")
        raise HTTPException(
            status_code=401,
            detail="Invalid Authorization header format. Expected: Bearer <token>",
        )

    print(f"got bearer {token}")

    # Validate token
    if not jwt_service.validate_token(token):
        logger.error("JWT token validation failed")
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    # Extract user info
    user_info = jwt_service.extract_user_info(token)
    if not user_info:
        logger.error("Failed to extract user info from token")
        raise HTTPException(status_code=401, detail="Invalid token claims")

    return user_info


class TicketBuyBody(BaseModel):
    flightNumber: str
    price: int
    paidFromBalance: bool


def error_response(msg, code):
    return JSONResponse(
        content=ErrorResponse(message=msg).model_dump(), status_code=code
    )


@app.get("/flights", response_model=PaginationResponse)
def get_flights(
    page: int = None,
    size: int = None,
    current_user: UserInfo = Depends(get_current_user),
):
    logger.debug(f"User {current_user.sub} accessed /flights")
    return flights_service.get_all(page, size)


def map_ticket_to_ticket_response(tick):
    flight = flights_service.get_flight_by_number(tick.flight_number)
    return TicketResponse(
        ticketUid=tick.ticket_uid,
        flightNumber=tick.flight_number,
        fromAirport=flight.fromAirport,
        toAirport=flight.toAirport,
        date=flight.date,
        price=flight.price,
        status=tick.status,
    )


@app.get("/tickets")
def get_tickets(
    current_user: UserInfo = Depends(get_current_user),
) -> List[TicketResponse]:
    logger.debug(f"User {current_user.sub} accessed /tickets")

    privilege = privileges_service.get_user_privelge(current_user.name)
    if privilege is None:
        return error_response("Пользователь не найден", 404)
    tickets_info = tickets_service.get_user_tickets(current_user.name)
    tickets = []
    for tick in tickets_info:
        tickets.append(map_ticket_to_ticket_response(tick))
    return tickets


@app.get("/me")
def get_user(
    current_user: UserInfo = Depends(get_current_user),
) -> UserInfoResponse | ErrorResponse:
    logger.debug(f"User {current_user.sub} accessed /me")

    privilege = privileges_service.get_user_privelge(current_user.name)
    if privilege is None:
        return error_response("Пользователь не найден", 404)
    tickets_info = tickets_service.get_user_tickets(current_user.name)
    tickets = []
    for tick in tickets_info:
        tickets.append(map_ticket_to_ticket_response(tick))
    return UserInfoResponse(
        tickets=tickets,
        privilege=PrivilegeShortInfo(
            balance=privilege.balance, status=privilege.status
        ),
    )


@app.get("/tickets/{ticket_uid}")
def get_ticket(
    ticket_uid: uuid.UUID,
    current_user: UserInfo = Depends(get_current_user),
) -> TicketResponse | ErrorResponse:
    ticket = tickets_service.get_ticket(ticket_uid)
    if ticket is None:
        return error_response("Билет не найден", 404)
    if ticket.username != current_user.name:
        return error_response("Билет не пренадлежит пользователю", 403)
    flight = flights_service.get_flight_by_number(ticket.flight_number)
    if flight is None:
        return error_response("Перелет не найден", 404)

    resp = TicketResponse(
        ticketUid=ticket.ticket_uid,
        flightNumber=ticket.flight_number,
        fromAirport=flight.fromAirport,
        toAirport=flight.toAirport,
        date=flight.date,
        price=ticket.price,
        status=ticket.status,
    )
    return resp


@app.post("/tickets")
def buy_ticket(
    body: TicketPurchaseRequest,
    current_user: UserInfo = Depends(get_current_user),
) -> TicketPurchaseResponse | ValidationErrorResponse:

    flight = flights_service.get_flight_by_number(body.flightNumber)
    if flight is None:
        return ValidationErrorResponse(message="Ошибка валидации данных", errors=[])

    priv = privileges_service.get_user_privelge(current_user.name)
    if priv is None:
        return ValidationErrorResponse(message="Пользователь не существует", errors=[])

    now = datetime.now()
    ticket_uid = uuid.uuid4()

    paid_by_money = flight.price
    paid_by_bonus = 0
    if body.paidFromBalance:
        money = min(priv.balance, flight.price)
        paid_by_bonus = money
        paid_by_money = flight.price - paid_by_bonus
        if paid_by_bonus:
            privileges_service.add_transaction(
                current_user.name,
                AddTranscationRequest(
                    privilege_id=priv.id,
                    ticket_uid=ticket_uid,
                    datetime=now,
                    balance_diff=paid_by_bonus,
                    operation_type="DEBIT_THE_ACCOUNT",
                ),
            )
    else:
        privileges_service.add_transaction(
            current_user.name,
            AddTranscationRequest(
                privilege_id=priv.id,
                ticket_uid=ticket_uid,
                datetime=now,
                balance_diff=paid_by_money // 10,
                operation_type="FILL_IN_BALANCE",
            ),
        )

    priv = privileges_service.get_user_privelge(current_user.name)
    tickets_service.create_ticket(
        ticket_uid, current_user.name, flight.flightNumber, paid_by_money
    )
    return TicketPurchaseResponse(
        ticketUid=ticket_uid,
        flightNumber=body.flightNumber,
        fromAirport=flight.fromAirport,
        toAirport=flight.toAirport,
        date=now,
        price=flight.price,
        paidByMoney=paid_by_money,
        paidByBonuses=paid_by_bonus,
        status="PAID",
        privilege=PrivilegeShortInfo(balance=priv.balance, status=priv.status),
    )


@app.delete("/tickets/{ticket_uid}", status_code=204)
def return_ticket(
    ticket_uid: uuid.UUID,
    current_user: UserInfo = Depends(get_current_user),
):
    ticket = tickets_service.get_ticket(ticket_uid)
    if ticket is None:
        return error_response("Билет не существует", 404)
    if ticket.username != current_user.name:
        return error_response("Билет не принадлежит пользователю", 403)
    if ticket.status != "PAID":
        return error_response("Билет не может быть отменен", 400)
    if privileges_service.get_user_privelge_transaction(current_user.name, ticket_uid):
        privileges_service.rollback_transaction(current_user.name, ticket_uid)
    tickets_service.delete_ticket(ticket_uid)


@app.get("/privilege")
def get_privilege(
    current_user: UserInfo = Depends(get_current_user),
) -> PrivilegeInfoResponse:
    print("current user", current_user)
    a = privileges_service.get_user_privelge(current_user.name)
    if a is None:
        return error_response("Пользователь не сущесвует", 404)
    b = privileges_service.get_user_privelge_history(current_user.name)
    his = []
    for it in b:
        his.append(
            BalanceHistory(
                date=it.datetime,
                ticketUid=it.ticket_uid,
                balanceDiff=it.balance_diff,
                operationType=it.operation_type,
            )
        )
    return PrivilegeInfoResponse(balance=a.balance, status=a.status, history=his)


@app.get("/manage/health", status_code=201)
def health():
    pass


@app.post("/authorize", response_model=TokenResponse)
def authorize(request: TokenRequest):
    """
    Authenticate user with username/password using ROPC flow.
    Returns JWT tokens from IdP.
    """

    token_response = auth_service.authenticate_user(
        username=request.username, password=request.password
    )

    if not token_response:
        logger.warning(f"Failed authentication attempt for user: {request.username}")
        raise HTTPException(status_code=401, detail="Invalid credentials")

    logger.info(f"Successful authentication for user: {request.username}")
    return token_response


@app.get("/callback")
def callback(code: str = None, state: str = None, error: str = None):
    """
    OAuth2 callback endpoint (for authorization code flow).
    Since we're using ROPC, this endpoint might not be used but is required.
    """
    # If using authorization code flow in the future
    if error:
        raise HTTPException(status_code=400, detail=f"OAuth error: {error}")

    return {"message": "Callback endpoint", "code": code, "state": state}
