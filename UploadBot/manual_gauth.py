import os
import pickle
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

# If modifying these SCOPES, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/drive']

def authenticate():
    """Handles the OAuth2 authentication process and stores the credentials for reuse."""
    creds = None

    # The file token.pickle stores the user's access and refresh tokens
    # and is created automatically when the authorization flow completes for the first time.
    # if os.path.exists('token.pickle'):
    #     with open('token.pickle', 'rb') as token:
    #         creds = pickle.load(token)

    # If there are no valid credentials available, prompt the user to log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            # Automatically refresh the credentials if expired
            creds.refresh(Request())
        else:
            # Initiate the authorization flow if no valid credentials
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)

        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    print("Authentication successful!")
    return creds

if __name__ == '__main__':
    authenticate()

