import argparse
import boto3
from textual.app import App, ComposeResult
from textual.widgets import Input, DataTable
from textual.widgets import Pretty, Static, Footer, Header
from textual.containers import Horizontal

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
        yield Pretty("")

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
        '''
        When the user selects a row we pull the parameter, 
        merge the response into the parameter list and display the value
        '''
        table = self.query_one(DataTable)
        results_view = self.query_one(Pretty)

        param_name = table.get_cell_at((event.cursor_row, 0))
        row_key = event.row_key.value

        response = self.client.get_parameter(
            Name = param_name,
            WithDecryption = True
        )

        # The row index matches the parameter list index so merge  
        # get_parameters response into matching list item. e.g row key 0 is list index 0
        self.parameters.list[row_key] = response['Parameter'] | self.parameters.list[row_key]

        #results_view.update(response['Parameter']['Value'])
        results_view.update(self.parameters.list[row_key])

    def on_data_table_row_highlighted(self, event):
        '''
        When a row is highlight (NOT selected) display the  
        corrisponding item in the paramter list
        '''
        results_view = self.query_one(Pretty)
        row_key = event.row_key.value

        results_view.update(self.parameters.list[row_key])

    def update_table(self, parameters ) -> None:
        '''
        Clear the table and add a row for each parameter that's been passed.
        '''

        table = self.query_one(DataTable)
        table.clear(columns = False)

        # Add parameter to the table. Set row key to be the index of the 
        # parameter in the list so we can cross referance later.
        for index, parameter in enumerate(parameters):
            if 'Description' not in parameter:
                parameter['Description'] = ""
            table.add_row(parameter['Name'], parameter['Description'], key = index)           
            
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