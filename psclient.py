import argparse
import pyperclip
import boto3
from botocore.exceptions import ClientError
from rich.text import Text
from textual.app import App, ComposeResult
from textual.widgets import Input, Button, DataTable
from textual.widgets import Pretty, Static, Footer
from textual.containers import Horizontal
from textual.worker import Worker

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
    
    async def refresh(self):
        self.list = []
        next_token = ' '

        while next_token is not None:
            try:
                ssm_details = self.client.describe_parameters(MaxResults = 50, NextToken = next_token)
                current_batch, next_token = self.get_resources_from(ssm_details)
                self.list += current_batch
            except ClientError as e:
                print(e.response['Error']['Code'])

        # Adding the list index as a key in the dict will prevent us needing
        # to repeatedly enumerate the list to find the index value later on
        for index, parameter in enumerate(self.list):
            parameter["IndexPosition"] = index
class SearchContainer(Static):
    
    def compose(self) -> ComposeResult:
        with Horizontal(id = "search"):
            yield Input(placeholder="Search for parameter")
            yield Button("Clear", variant="default")

        dt = DataTable()
        dt.cursor_type = "row"
        dt.add_columns("Parameter name", "Description")
        yield dt

class ResultsContainer(Static):
    
    def compose(self) -> ComposeResult:
        yield Pretty("")

class psSearch(App):

    CSS_PATH = "pyclient.tcss"
    BINDINGS = [
        ("ctrl-c", "quit", "Quit"),
        ("f5", "refresh_table()", "Refresh parameters"),
        ("f6", "copy_to_clipboard()", "Copy value to clipboard")
    ]

    def action_refresh_table(self) -> None:
        '''
        Keybing action connected to F5
        '''
        self.display_loading_indicator(True)
        self.run_worker(self.parameters.refresh(), thread = True)

    def action_copy_to_clipboard(self):        
        if 'Value' in self.parameters.list[self.highlighted_row_key]:
            pyperclip.copy(self.parameters.list[self.highlighted_row_key]['Value'])

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield SearchContainer(classes="column")
            yield ResultsContainer(classes="column") 
        yield Footer()    

    def on_button_pressed(self, event: Button.Pressed) -> None:
        input = self.query_one(Input)
        input.clear()

    def on_input_changed(self, event: Input.Changed) -> None:
        '''
        On each keystroke filter the parameter list with the
        input box value and refresh the data table.
        '''
        search_terms = event.value.split()
        filtered_parameter_list = [
            item 
            for item in self.parameters.list
            if all((term in item['Name']) for term in search_terms)
        ]

        self.update_table(filtered_parameter_list)

    # def on_key(self, event: events.Key) -> None:
    #     if event.key == "f5":
    #         self.parameters.refresh()
    #         self.update_table(self.parameters.list)

    def on_data_table_row_selected(self, event):
        '''
        When the user selects a row we pull the parameter, 
        merge the response into the parameter list and display the value
        '''
        table = self.query_one(DataTable)
        results_view = self.query_one(Pretty)

        # Cast to string in case the cell has previously been set to a Text object
        param_name = str(table.get_cell_at((event.cursor_row, 0)))
        description = str(table.get_cell_at((event.cursor_row, 1)))

        row_key = event.row_key.value
        
        try:
            response = self.client.get_parameter(
                Name = param_name,
                WithDecryption = True
            )
        except ClientError as e:
            print(e.response['Error']['Code'])
        
        # The row index matches the parameter list index so merge  
        # get_parameters response into matching list item. e.g row key 0 is list index 0
        self.parameters.list[row_key] = response['Parameter'] | self.parameters.list[row_key]

        #results_view.update(response['Parameter']['Value'])
        results_view.update(self.parameters.list[row_key])

        table.update_cell_at((event.cursor_row, 0), Text(param_name, style = "green"))
        table.update_cell_at((event.cursor_row, 1), Text(description, style = "green"))

    def on_data_table_row_highlighted(self, event):
        '''
        When a row is highlight (NOT selected) display the  
        corrisponding item from the paramter list
        '''
        results_view = self.query_one(Pretty)
        row_key = event.row_key.value

        print(f"ROW KEY IS {row_key}")
        print(f"PARAMETER IS {self.parameters.list[row_key]}")

        results_view.update(self.parameters.list[row_key])
        # Track the highlighted row. We'll use this elsewhere
        self.highlighted_row_key = row_key

    def update_table(self, parameters) -> None:
        '''
        Clear the table and add a row for each parameter that's been passed.
        '''        
        table = self.query_one(DataTable)
        table.clear(columns = False)

        # Add parameter to the table. Set row key to be the index of the 
        # parameter in the list so we can cross referance later.
        for parameter in parameters:
            if 'Description' not in parameter:
                parameter['Description'] = ""

            if 'Value' in  parameter:
                name = Text(parameter['Name'], style = "green")
                description = Text(parameter['Description'], style = "green")
            else:
                name = parameter['Name']
                description = parameter['Description']

            table.add_row(name, description, key = parameter['IndexPosition'])           

        # Clear loading indicator    
        self.display_loading_indicator(False)

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        """Called when the worker state changes."""
        if event.worker.is_finished:
            self.update_table(self.parameters.list)

    def display_loading_indicator(self, status):
        table = self.query_one(DataTable)
        table.loading = status        

    def on_mount(self) -> None:
        '''
        On startup create the parameter list object,
        pull the parameters and update the table. Data load
        will be handled asyncronizely to the GUI startup.
        '''
        
        session = BotoWrapper()
        self.client = session.getclient()

        self.parameters = Parameters(self.client)
        self.run_worker(self.parameters.refresh(), thread = True)

        self.display_loading_indicator(True)

if __name__ == "__main__":
    app = psSearch()
    app.run()