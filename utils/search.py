from textual.widgets import Input, OptionList


def search_function(object, event: Input.Changed, iterables) -> None:
    """search helper function
        :param object: self instance of class Input
        :param event: event of class Input
        :param iterables: the song/ album list
    """
    query = event.value.lower()

    filtered = [a for a in iterables if query in a.lower()]

    option_list = object.query_one(OptionList)
    option_list.clear_options()
    for song_or_album in filtered:
        option_list.add_option(song_or_album)