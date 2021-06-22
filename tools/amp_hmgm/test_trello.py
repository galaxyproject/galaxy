from trello import TrelloClient
from trello.card import Card
import trello
import requests

def main():
    # Vars to reference
    api_key = "API_KEY"
    api_token = "API_Token"
    board_id = "BOARD ID"
    todo_list_id = "TODO LIST_ID"
    done_list_id = "DONE LIST ID"

    client = TrelloClient(
        api_key=api_key,
        token=api_token
    )

    # Get a list of boards
    all_boards = client.list_boards()

    # Print a list of boards 
    for board in all_boards:
        print(board.id + ":" + board.name)

    # Get our board
    amp_board = client.get_board(board_id)
    print_lists(amp_board)
    # Get the todo list
    todo_list = get_todo_list(amp_board, todo_list_id)
    created_card = create_card(client, todo_list)
    done_list = get_done_list(amp_board, done_list_id)

    # Move the list from TODO to Done list
    move_card(api_key, api_token, created_card.id, done_list)

    exit(0)
def print_lists(amp_board):
    lists = amp_board.list_lists()
    for l in lists:
        print("List id: " + l.id + " name: " + l.name)
# Get the todo list object
def get_todo_list(amp_board, todo_list_id):
    lists = amp_board.list_lists()
    for l in lists:
        if l.id == todo_list_id:
            return l

# Get the done list object
def get_done_list(amp_board, done_list_id):
    lists = amp_board.list_lists()
    for l in lists:
        if l.id == done_list_id:
            return l

# Create a card in a list
def create_card(client, list):
    c = list.add_card(name="Test Card 1", desc="https://google.com")
    print("Card created - id: " + c.id + " name: " + c.name)
    return c

# This uses a direct put request...I couldn't find a method in the python package to do this
def move_card(api_key, api_token, card_id, target_list):
    requests.put("https://api.trello.com/1/cards/" + card_id, params=dict(key=api_key, token=api_token), data=dict(idList=target_list.id))

if __name__ == "__main__":
	main()   