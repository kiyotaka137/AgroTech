ensemble = None

def set_ensemble(model):
    global ensemble
    ensemble = model

def ensemble_predict(X):
    global ensemble
    return ensemble.predict(X)