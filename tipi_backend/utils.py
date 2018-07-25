from datetime import datetime

from tipi_backend.database.models.searches_tracker import SearchesTracker


def save_search(params, metadata):
    def extract_value_from_metadata(key):
        try:
            return str(metadata[key])
        except:
            return ""

    def is_valid(key, value):
        empty = [None, '', []]
        hidden_fields = ['per_page', 'page']
        return value not in empty and key not in hidden_fields

    try:
        # Only saves the first search
        if params['page'] is not 1:
            return
        st = SearchesTracker(
                date = datetime.now(),
                fields = [key for key in params.keys() if is_valid(key, params[key])],
                values = {key: value for key, value in params.items() if is_valid(key, value)},
                metadata = {
                    'ip': extract_value_from_metadata('HTTP_X_REAL_IP'),
                    'user_agent': extract_value_from_metadata('HTTP_USER_AGENT')
                    }
                )
        st.save()
    except Exception as e:
        print("Exception: " + str(e))
        # Do not save the search and continue
        pass
