import pickle


def fetch_data():
    with open("./assets/data.pkl", "rb") as handle:
        data = pickle.load(handle)
        return data
