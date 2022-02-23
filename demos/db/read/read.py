# Import some classes from the autonomy_toolkit module
from autonomy_toolkit.db import ATKDataFileReader, register_type

# The autonomy_toolkit data directory we'll read
# The sqlite needs to have the custom message types
filename = 'data/'

# Register the types that we need
register_type("data/VehicleInput.msg", "custom_msgs/msg/VehicleInput")

# -----------------------------------
# Read through the newly created file
# -----------------------------------

# You can use a generator
with ATKDataFileReader(filename) as reader:
    for timestamp, connection, msg in reader:
        print(timestamp, msg)

# Or you can use pandas
with ATKDataFileReader(filename) as reader:
    df = reader.convert_to_pandas_df()
    print(df)
