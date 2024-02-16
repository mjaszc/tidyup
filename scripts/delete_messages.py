import os.path
import re

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.discovery import Resource
from googleapiclient.errors import HttpError


# If modifying these scopes, delete the file token.json.
# https://developers.google.cn/gmail/api/auth/scopes?hl=en#:~:text=Gmail%20API%20scopes%20To%20define%20the%20level%20of,data%20it%20accesses%2C%20and%20the%20level%20of%20access.
SCOPES = [
    "https://mail.google.com/",
    "https://www.googleapis.com/auth/gmail.readonly",
]


def get_unique_senders(service: Resource, messages_list: list) -> set[str]:
    """
    This function finds all unique sender email addresses from a list of message IDs.

    Args:
        service: An authorized Gmail API service object.
        messages_list: A list of dictionaries containing message IDs (e.g., from a Gmail API response).

    Returns:
        A set containing all unique sender email addresses found in the messages.
    """
    unique_senders = set()

    for mess in messages_list:
        message_data = (
            service.users()
            .messages()
            .get(userId="me", id=mess["id"], format="full")
            .execute()
        )
        for header in message_data["payload"]["headers"]:
            if header["name"] == "From":
                if header["value"] not in unique_senders:
                    unique_senders.add(header["value"])

    return unique_senders


def mark_senders(senders_list: list[str]) -> list[str]:
    """
    This function interactively marks senders for further processing.

    Args:
        senders_list: A list of sender names and addresses.

    Returns:
        A list containing only the marked senders.
    """
    marked_senders = []
    for item in senders_list:
        # The function now ensures that only valid input ("y" or "n") is accepted before proceeding.
        while True:
            mark = input(f"Do you want to mark '{item}'? (y/n): ").lower()
            if mark in ("y", "n"):
                break
            print("Invalid input. Please enter 'y' or 'n'.")

        if mark == "y":
            marked_senders.append(item)

    return marked_senders


def get_marked_senders_msg_id(
    service: Resource, messages_list: list, senders: list
) -> list[str]:
    """
    Returns a list of message IDs from the given list that were sent by one of the senders in the senders list.

    Args:
        service: The Gmail service object.
        messages_list: A list of message IDs.
        senders: A list of email addresses.

    Returns:
        A list of message IDs.
    """
    unique_senders_msgs_id = []

    for mess in messages_list:
        message_data = (
            service.users()
            .messages()
            .get(userId="me", id=mess["id"], format="full")
            .execute()
        )

        for header in message_data["payload"]["headers"]:

            if header["name"] == "From":
                # Check if the iterated item sender's email address is in the senders list.
                if header["value"] in senders:
                    unique_senders_msgs_id.append(message_data["id"])

    return unique_senders_msgs_id


def extract_emails(senders: set[str]) -> list[str]:
    """
    Extracts email addresses from a set of strings.

    Args:
        senders: A set of strings containing sender name and addresse.

    Returns:
        A list containing the extracted email addresses.
    """
    emails = []
    for text in senders:
        email_match = re.search(r"<(.*?)>", text)  # Extract email within angle brackets
        if email_match:
            email = email_match.group(1)
            emails.append(email)
    return emails


def main():
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    try:
        # Create gmail api client
        service = build("gmail", "v1", credentials=creds)

        messages = (
            service.users().messages().list(userId="me").execute().get("messages")
        )

        senders = mark_senders(get_unique_senders(service, messages))

        get_marked_senders_msg_id(service, messages, senders)

        # Getting project root directory
        cwd = os.getcwd()
        # Deleting token.json file after successful execution
        os.remove(f"{cwd}/token.json")

    except HttpError as error:
        print(f"An error occurred: {error}")


if __name__ == "__main__":
    main()