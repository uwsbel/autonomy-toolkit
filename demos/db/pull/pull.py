# Import some classes from the av module
from avtoolbox.db import AVDatabase
from avtoolbox.utils.logger import LOGGER, set_verbosity

# Other imports
import os

# Set the verbosity to log everything
set_verbosity(2)

# Instantiate the database
db = AVDatabase("data")

# Push a local file to the database
ls = db.ls()
bag = db.pull(ls[0])

# Make sure it is present in the current working directory
print(bag.db_name in os.listdir('.'))
