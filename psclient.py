import argparse
import boto3
from textual.app import App, ComposeResult
from textual.widgets import Input, DataTable
from textual.widgets import Pretty, Static, Footer, Header
from textual.containers import Horizontal

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

class Parameters():

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

class SearchContainer(Static):
    
    def compose(self) -> ComposeResult:
        yield Input(placeholder="Search for paramater")

        dt = DataTable()
        dt.cursor_type   = "row"
        yield dt


class ResultsContainer(Static):
    
    def compose(self) -> ComposeResult:
            yield Pretty(DATA)

class psSearch(App):

    CSS_PATH = "pyclient.css"

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield SearchContainer(classes="column")
            yield ResultsContainer(classes="column")
        yield Footer()    

    def on_input_changed(self, event: Input.Changed) -> None:
        # on each keystore filter the parameter list with the
        # input boc value and refresh the data table.
        filtered_parameter_list = [
            item for item in self.parameters.list if event.value in item['Name']
        ]
        self.update_table(filtered_parameter_list)

    def update_table(self, parameters ) -> None:
        # Clear the table and add arow for each parameter
        table = self.query_one(DataTable)
        table.clear(columns = True)
        table.add_columns("Parameter name", "Description")

        for parameter in parameters:
            if 'Description' not in parameter:
                parameter['Description'] = ""
            table.add_row(parameter['Name'], parameter['Description'])           

    def on_mount(self) -> None:
        # On startup create the parameter list object,
        # pull the parameters and update the table
        self.parameters = Parameters()
        self.parameters.refresh()
        self.update_table(self.parameters.list)

if __name__ == "__main__":
    app = psSearch()
    app.run()