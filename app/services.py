from common import *
import requests


class FlightsService:
    def __init__(self, url):
        self.url = url

    def healthcheck(self):
        response = requests.get(f"{self.url}/manage/health")
        response.raise_for_status()

    def get_all(self, page: int = None, size: int = None):
        response = requests.get(
            f"{self.url}/flights", params={"page": page, "size": size}
        )
        response.raise_for_status()
        return PaginationResponse.model_validate(response.json())

    def get_flight_by_number(self, flight_number: str) -> FlightResponse:
        response = requests.get(f"{self.url}/flights/{flight_number}")
        response.raise_for_status()
        return FlightResponse.model_validate(response.json())


class TicketsService:
    def __init__(self, url):
        self.url = url

    def healthcheck(self):
        response = requests.get(f"{self.url}/manage/health")
        response.raise_for_status()

    def get_user_tickets(self, username) -> list[Ticket]:
        response = requests.get(f"{self.url}/tickets/user/{username}")
        response.raise_for_status()
        return [Ticket.model_validate(x) for x in response.json()]

    def get_ticket(self, ticket_uid) -> Ticket | None:
        response = requests.get(f"{self.url}/tickets/{ticket_uid}")
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return Ticket.model_validate(response.json())

    def delete_ticket(self, ticket_uid) -> None:
        response = requests.delete(f"{self.url}/tickets/{ticket_uid}")
        response.raise_for_status()

    def create_ticket(self, ticket_uid, username, flight_number, price):
        response = requests.post(
            f"{self.url}/tickets",
            json=TicketCreateRequest(
                ticketUid=ticket_uid,
                username=username,
                flightNumber=flight_number,
                price=price,
            ).model_dump(mode="json"),
        )
        response.raise_for_status()


class PrivilegesService:
    def __init__(self, url):
        self.url = url

    def healthcheck(self):
        response = requests.get(f"{self.url}/manage/health")
        response.raise_for_status()

    def get_user_privelge(self, username) -> Privilege:
        response = requests.get(f"{self.url}/privilege/{username}")
        if response.status_code == 404:
            return None
        response.raise_for_status()
        privilege = Privilege.model_validate(response.json())
        return privilege

    def get_user_privelge_history(self, username) -> list[PrivilegeHistory]:
        response = requests.get(f"{self.url}/privilege/{username}/history")
        response.raise_for_status()
        return [PrivilegeHistory.model_validate(x) for x in response.json()]

    def get_user_privelge_transaction(self, username, ticket_uid) -> PrivilegeHistory:
        response = requests.get(f"{self.url}/privilege/{username}/history/{ticket_uid}")
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return PrivilegeHistory.model_validate(response.json())

    def add_transaction(self, username, data: AddTranscationRequest):
        response = requests.post(
            f"{self.url}/privilege/{username}/history",
            json=data.model_dump(mode="json"),
        )
        response.raise_for_status()

    def rollback_transaction(self, username, ticket_uid):
        response = requests.delete(
            f"{self.url}/privilege/{username}/history/{ticket_uid}"
        )
        response.raise_for_status()
