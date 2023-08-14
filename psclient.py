import argparse
import boto3
from textual.app import App, ComposeResult
from textual.widgets import Input, DataTable
from textual.widgets import Pretty, Static, Footer, Header
from textual.containers import Horizontal

ROWS = [
    ("lane", "swimmer", "country", "time"),
    (4, "Joseph Schooling", "Singapore", 50.39),
    (2, "Michael Phelps", "United States", 51.14),
    (5, "Chad le Clos", "South Africa", 51.14),
    (6, "László Cseh", "Hungary", 51.14),
    (3, "Li Zhuhao", "China", 51.26),
    (8, "Mehdy Metella", "France", 51.58),
    (7, "Tom Shields", "United States", 51.73),
    (1, "Aleksandr Sadovnikov", "Russia", 51.84),
    (10, "Darren Burns", "Scotland", 51.84),
]

DATA = {
    "title": "Back to the Future",
    "releaseYear": 1985,
    "director": "Robert Zemeckis",
    "genre": "Adventure, Comedy, Sci-Fi",
    "cast": [
        {"actor": "Michael J. Fox", "character": "Marty McFly"},
        {"actor": "Christopher Lloyd", "character": "Dr. Emmett Brown"},
    ]
}

class Paramaters():

    list = []

    def get_resources_from(self, ssm_details):
        results = ssm_details['Parameters']
        resources = [result for result in results]
        next_token = ssm_details.get('NextToken', None)
        return resources, next_token
    
    def get_session(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("--profile", help = "AWS cli profile to connect aws with.")
        parser.add_argument("--region", help = "Set AWS region.")
        args = parser.parse_args()
    
        if args.profile:
            session = boto3.Session(profile_name = args.profile)
        else:    
            session = boto3.Session()

        client = session.client('ssm')
    
        return client
    
    def refresh(self):
        client = self.get_session()
        next_token = ' '

        while next_token is not None:
            ssm_details = client.describe_parameters(MaxResults = 50, NextToken = next_token)
            current_batch, next_token = self.get_resources_from(ssm_details)
            self.list += current_batch
        
    def __init__(self):
        self.parameters = self.refresh()

class Search(Static):
    
    def compose(self) -> ComposeResult:
        yield Input(placeholder="Search for paramater")

        dt = DataTable()
        dt.cursor_type   = "row"
        yield dt

class Results(Static):
    
    def compose(self) -> ComposeResult:
            yield Pretty(DATA)

class psSearch(App):

    CSS_PATH = "pyclient.css"

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield Search(classes="column")
            yield Results(classes="column")
        yield Footer()    


    def on_mount(self) -> None:
    # On start up we set up the boto3 session 
    # and call a table refresh. This will load
    # the table with all available parameters    

        parameter = Paramaters()

        table = self.query_one(DataTable)
        table.add_columns("Parameter name", "Description")

        for parameter in parameter.list:
            if 'Description' not in parameter:
                parameter['Description'] = ""
            table.add_row(parameter['Name'], parameter['Description'])        

if __name__ == "__main__":

    app = psSearch()
    app.run()