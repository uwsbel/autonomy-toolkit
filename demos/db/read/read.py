# Import some classes from the av module
from avtoolbox.db import AVDataFileReader, register_type

# The av data directory we'll read
# The sqlite needs to have the custom message types
filename = 'data/'

# Register the types that we need
register_type("data/VehicleInput.msg", "custom_msgs/msg/VehicleInput")

# -----------------------------------
# Read through the newly created file
# -----------------------------------

# You can use a generator
with AVDataFileReader(filename) as reader:
    for timestamp, connection, msg in reader:
        print(timestamp, msg)

# Or you can use pandas
with AVDataFileReader(filename) as reader:
    df = reader.convert_to_pandas_df()
    print(df)
