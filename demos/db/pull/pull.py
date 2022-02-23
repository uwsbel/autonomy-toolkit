# Import some classes from the autonomy_toolkit module
from autonomy_toolkit.db import ATKDatabase
from autonomy_toolkit.utils.logger import LOGGER, set_verbosity

# Other imports
import os

# Set the verbosity to log everything
set_verbosity(2)

# Instantiate the database
db = ATKDatabase("data")

# Push a local file to the database
ls = db.ls()
bag = db.pull(ls[0])

# Make sure it is present in the current working directory
print(bag.db_name in os.listdir('.'))
