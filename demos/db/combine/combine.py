# Import some classes from the avtoolbox module
from avtoolbox.db import AVDataFile, AVDataFileReader
from avtoolbox.ros.messages import MessageType
from avtoolbox.utils.logger import LOGGER

# Other imports
import shutil
from pathlib import Path

# Initialize the configuration object
# The ros1bag file is the actual bag file. The ros2 one is the directory.
# The yaml file in that directory points to the db3 for ros2 parsing.
ros1bag = 'data/ros1.bag'
ros2bag = 'data/'
output = 'combine_demo'
ros2_types = [MessageType(file='data/VehicleInput.msg', name='custom_msgs/msg/VehicleInput')]  # noqa

# Run the combine command
if Path(output).exists():
    LOGGER.warning(f"'{output}' already exists. Deleting it...")
    shutil.rmtree(output)
AVDataFile.combine(ros1bag, ros2bag, output, ros2_types=ros2_types)

# -----------------------------------
# Read through the newly created file
# -----------------------------------

# You can use a generator
with AVDataFileReader(output) as reader:
    for timestamp, connection, msg in reader:
        print(timestamp, msg)

# Or you can use pandas
with AVDataFileReader(output) as reader:
    df = reader.convert_to_pandas_df()
    print(df)
