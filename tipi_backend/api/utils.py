def get_unique_values(model, field):
    values = model.objects().distinct(field)
    values.remove('')
    return sorted(values)
