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

# class Boto3Wrapper:
#     def __init__(self, service_name, region_name):
#         self.client = boto3.client(service_name, region_name=region_name)
#         self.resource = boto3.resource(service_name, region_name=region_name)

#     def __getattr__(self, name):
#         # Check if the method exists in the client
#         if hasattr(self.client, name):
#             return getattr(self.client, name)
#         # Check if the method exists in the resource
#         elif hasattr(self.resource, name):
#             return getattr(self.resource, name)
#         else:
#             raise AttributeError("'Boto3Wrapper' object has no attribute '{}'".format(name))

#     def set_client(self, service_name, region_name):
#         #Set the client to a new service and region
#         self.client = boto3.client(service_name, region_name=region_name)

#     def set_resource(self, service_name, region_name):
#         #Set the resource to a new service and region
#         self.resource = boto3.resource(service_name, region_name=region_name)

#     def get_client(self):
#         #Get the current client
#         return self.client

#     def get_resource(self):
#         #Get the current resource
#         return self.resource


class BotoWrapper():

    def getclient(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("--profile", help = "AWS cli profile to connect aws with.")
        parser.add_argument("--region", help = "Set AWS region.")
        args = parser.parse_args()
    
        if args.profile:
            session = boto3.Session(profile_name = args.profile)
        else:    
            session = boto3.Session()

        self.client = session.client('ssm')
        return self.client
class Parameters():

    list = []

    def __init__(self, client):
        self.client = client

    def get_resources_from(self, ssm_details):
        results = ssm_details['Parameters']
        resources = [result for result in results]
        next_token = ssm_details.get('NextToken', None)
        return resources, next_token
    
    def refresh(self):
        next_token = ' '

        while next_token is not None:
            ssm_details = self.client.describe_parameters(MaxResults = 50, NextToken = next_token)
            current_batch, next_token = self.get_resources_from(ssm_details)
            self.list += current_batch

class SearchContainer(Static):
    
    def compose(self) -> ComposeResult:
        yield Input(placeholder="Search for paramater")

        dt = DataTable()
        dt.cursor_type = "row"
        dt.add_columns("Parameter name", "Description")
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
        # on each keystroke filter the parameter list with the
        # input box value and refresh the data table.
        search_terms = event.value.split()
        filtered_parameter_list = [
            item 
            for item in self.parameters.list
            if all((term in item['Name']) for term in search_terms)
        ]

        self.update_table(filtered_parameter_list)

    def on_data_table_row_selected(self, event):
        table = self.query_one(DataTable)
        results = self.query_one(Pretty)

        param_name = table.get_cell_at((event.cursor_row, 0))
        #self.client = Parameters.client

        response = self.client.get_parameter(
            Name = param_name,
            WithDecryption = True
        )
        results.update(response)

    def update_table(self, parameters ) -> None:
        # Clear the table and add arow for each parameter
        table = self.query_one(DataTable)
        table.clear(columns = False)

        for parameter in parameters:
            if 'Description' not in parameter:
                parameter['Description'] = ""
            table.add_row(parameter['Name'], parameter['Description'])           

    def on_mount(self) -> None:
        # On startup create the parameter list object,
        # pull the parameters and update the table
        session = BotoWrapper()
        self.client = session.getclient()

        self.parameters = Parameters(self.client)
        self.parameters.refresh()

        self.update_table(self.parameters.list)

if __name__ == "__main__":
    app = psSearch()
    app.run()