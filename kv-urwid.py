import boto3
from urllib.parse import urlparse
import sys
import base64
import argparse
import urwid
import pyperclip
from time import sleep
from custom_widgets import ListEntry


class bcolors():
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[0;93m'
    WARNING = '\033[93m'
    RED = '\033[91m'
    RESET = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    BACKGROUND = '\033[100m'
    BACKGROUND_GRAY = '\033[48;5;235m'

class kvDisplay():

    PALETTE = [
        ('input expr', 'black,bold', 'light gray'),
        ('bigtext', 'light blue', 'black'),
        ('highlight', 'white', 'dark gray'),
        ('secret_pulled', 'light green', 'dark gray'),
        ('greentext', 'light green', ''),
        ('buttons', 'light blue', 'black'),
        ('button_click', 'white', 'black')

    ]

    def __init__(self, config, output_mode='result'):
        self.config = config
        self.master_list = master_list
        self.view = None
        self.output_mode = output_mode
        self.last_result = None

    def _get_font_instance(self):
        return urwid.get_all_fonts()[-2][1]()


    def get_secret(self, secret_name, button):
        response = config.get_parameter(
            Name = secret_name,
            WithDecryption = True
        )

        tag_response = config.list_tags_for_resource(
            ResourceType = 'Parameter',
            ResourceId = response['Parameter']['Name']
        )
        button.set_text(('secret_pulled', secret_name))

        return response, tag_response

    def is_base64(self, s):
        #base64decode/encode wants a byte sequence not a string
        s = (s.encode('utf-8'))
        
        try:
            return base64.b64encode(base64.b64decode(s)) == s
        except Exception:
            return False

    # Display the secret stored in the button
    def display_secret(self, button):
        if button.secret_value == '':
            self.secret_header.set_text('')
            self.secret.set_text('')
            self.secret_details.set_text('')
            self.secret_tags.set_text('')
            #self.secret_decoded.set_text('')
        # elif button.secret_value_decoded != '': 
        #     self.secret_details.set_text(('greentext', button.secret_value))
        #     self.secret.set_text('This secret is base64 encoded. Here\'s the decoded version:')
        #     self.secret_decoded.set_text(('greentext', button.secret_value_decoded))  
        else:
            self.secret_header.set_text('Value:')
            self.secret.set_text(('greentext', button.secret_value['Parameter']['Value']))
            self.secret_details.set_text(
                f"Properties:\n\n"
                f"Version: {button.secret_value['Parameter']['Version']}\n"
                f"Last modified: {button.secret_value['Parameter']['LastModifiedDate']}\n"
                f"Type: {button.secret_value['Parameter']['Type']}\n"
                f"ARN: {button.secret_value['Parameter']['ARN']}\n"
                f"Data type: {button.secret_value['Parameter']['DataType']}\n"
            )

            if button.secret_tags['TagList']:
                string = 'Tags:\n\n'
                for tag in button.secret_tags['TagList']:
                    string += f"{tag['Key']}: {tag['Value']}\n"
            
                self.secret_tags.set_text(string)


    def handle_enter(self, button, other):
        '''
        Add the parameter values to the button object
        and pass it to display_secret
        '''
        #self.secret_details.set_text('Retrieving secret...')
        button.secret_value, button.secret_tags = self.get_secret(button.secret_name, button)
        #if self.is_base64(button.secret_value):
        #    button.secret_value_decoded = base64.b64decode(button.secret_value).decode()
        self.display_secret(button)

    def handle_modifcation(self, listBox):
        '''
        listBox.focus returns AttrMap object wrapping the button.
        use base_widget to access the button object and pass it to display_secret
        Don't preform any action if the focus_position is the divider
        '''
        if listBox.focus_position != 0:
            self.display_secret(listBox.focus.base_widget)

    def listbox_secrets(self, list):
        '''
        Create a button for each entry in "list"
        '''
        for c in list:
            button = ListEntry(c)
            urwid.connect_signal(button, 'click', self.handle_enter, user_args = [button])
            self.list_walker.contents.append(urwid.AttrMap(button, None, focus_map = 'highlight'))

    def _create_view(self):

        #### header
        self.input_expr = urwid.Edit(('input expr', 'Search secrets: '))

        sb = urwid.BigText('PS Client', self._get_font_instance())
        sb = urwid.Padding(sb, 'center', None)
        sb = urwid.AttrWrap(sb, 'bigtext')
        sb = urwid.Filler(sb, 'top', None, 5)
        self.status_bar = urwid.BoxAdapter(sb, 5)

        div = urwid.Divider()
        self.header = urwid.Pile([self.status_bar, div,
            urwid.AttrMap(self.input_expr, 'input expr'), div],
            focus_item=2)

        urwid.connect_signal(self.input_expr, 'postchange', self._on_search)

        #### content

        body = [urwid.Divider()]
        walker = urwid.SimpleListWalker(body)
        listbox = urwid.ListBox(walker)
        # pass the whole listbox to the handler.
        # A scroll counts as a modification
        urwid.connect_signal(walker, "modified", self.handle_modifcation, user_args = [listbox] )  

        self.listbox = listbox 
        self.list_walker = walker
        self.left_content = urwid.ListBox(self.list_walker)
        self.left_content = urwid.LineBox(self.left_content, title='Parameter list')        
        self.listbox_secrets(master_list)

        self.secret_header = urwid.Text('')
        self.secret = urwid.Text('')
        self.secret_details = urwid.Text('')
        self.secret_tags = urwid.Text('')

        self.secret_details_display = [
            self.secret_header,
            div,
            self.secret,
            div,
            div,
            self.secret_details,
            div,
            div,
            self.secret_tags
        ]

        self.right_content = urwid.ListBox(self.secret_details_display)
        self.right_content = urwid.LineBox(self.right_content, title='Parameter details')

        self.content = urwid.Columns([('weight',1.5, self.left_content), self.right_content])
        
        #### footer
        self.footer_status = urwid.Text("Status: {} secrets loaded".format(str(len(self.list_walker.contents)-1))) #-1 for divider

        self.copy_button = urwid.Button('F7 - Copy to clipboard')
        urwid.connect_signal(self.copy_button, 'click', self.copy_to_clipboard)
        self.copy_button = urwid.AttrMap(self.copy_button, 'buttons' ) 

        # self.delete_button = urwid.Button('  F8 - Delete secret')
        # urwid.connect_signal(self.delete_button, 'click', self.copy_to_clipboard)
        # self.delete_button = urwid.AttrMap(self.delete_button, 'buttons') 

        self.footer_gridflow = urwid.GridFlow([self.copy_button], 26, 2, 0, 'left')
        self.footer = urwid.Columns([('weight',1.5, self.footer_status), self.footer_gridflow])

        #### frame config
        
        self.view = urwid.Frame(body=self.content, header=self.header,
                                footer=self.footer, focus_part='header')

    def _on_search(self, widget, text):
        filtered_master_list = []
        # Delete everything in the list bar the divider at index 0
        del self.list_walker.contents[1:len(self.list_walker.contents)]

        # If the search box is blank, display all secrets
        # else display secrets that match the content of the search box
        if not self.input_expr.get_edit_text():
            self.listbox_secrets(self.master_list)
        else:
            user_input = self.input_expr.get_edit_text().split()
            for index,item in enumerate(master_list):
                if all(x in item['Name'] for x in user_input):
                    filtered_master_list.append(master_list[index])
            self.listbox_secrets(filtered_master_list)
        
        self.footer_status.set_text("Status: {} secrets returned".format(str(len(self.list_walker.contents)-1))) #-1 for divider

    def copy_to_clipboard(self, button):
        value = self.listbox.focus.base_widget.secret_value['Parameter']['Value']
        selected_secret = self.listbox.focus.base_widget.secret_name
        
        if value != '':
            pyperclip.copy(value)
            self.footer_status.set_text("Status: {} copied to clipboard".format(selected_secret))

        # Make the button flash briefly on click. There is probably a better way to do this.
        # self.copy_button.base_widget.set_label(('button_click', 'F7 - Copy to clipboard'))
        # sleep(2.0)
        # self.copy_button.base_widget.set_label(('bigtext', 'F7 - Copy to clipboard'))



    def main(self, screen=None):
        self._create_view()
        self.loop = urwid.MainLoop(self.view, self.PALETTE,
                                    unhandled_input=self.unhandled_input,
                                    screen=screen)
        self.loop.screen.set_terminal_properties(colors=256)
        self.loop.run()

    def unhandled_input(self, key):
        if key == 'esc':
            raise urwid.ExitMainLoop()
        elif key == 'tab':
            current_pos = self.view.focus_position
            if current_pos == 'header':
                self.view.focus_position = 'body'
            else:
                self.view.focus_position = 'header'
        elif key == 'f7':
            # Do this globally so we can grab the secret regarless of what's in focus.
            # Running keypress instead of calling copy_to_clipboard to avoid issues with passed variables
            # 0 is the required 'size' paramater. Don't know what this does - 0 seems to work fine.
            self.copy_button.keypress(0, 'enter')


def main(master_list, config):

    screen = urwid.raw_display.Screen()
    display = kvDisplay(master_list, config)
    display.main(screen=screen)


#############################



subscription_ids = []
keyvault_list = []

parser = argparse.ArgumentParser()
parser.add_argument("--profile", help="AWS cli profile to connect aws with.")
# parser.add_argument("--id", help="Access key ID ")
# parser.add_argument("--secret", help="Access key ID ")

args = parser.parse_args()


def get_resources_from(ssm_details):
    results = ssm_details['Parameters']
    resources = [result for result in results]
    next_token = ssm_details.get('NextToken', None)
    return resources, next_token

print("Loading parameters...\n")

# Pick up a profile, id/key, or let boto3 search for defaults/environment variables
if args.profile:
    session = boto3.Session(profile_name = args.profile)
# elif args.id and args.secret:
#     session = boto3.Session(
#         aws_access_key_id = args.id,
#         aws_secret_access_key = args.secret,
#     )
else:    
    session = boto3.Session()

config = session.client('ssm', region_name = 'eu-west-1')
next_token = ' '
master_list = []
while next_token is not None:
    ssm_details = config.describe_parameters(MaxResults = 50, NextToken = next_token)
    current_batch, next_token = get_resources_from(ssm_details)
    master_list += current_batch


if __name__ == '__main__':
    sys.exit(main(master_list, config))