# Import some classes from the autonomy_toolkit module
from autonomy_toolkit.db import ATKDatabase
from autonomy_toolkit.utils.logger import LOGGER, set_verbosity

# Set the verbosity to log everything
set_verbosity(2)

# Instantiate the database
db = ATKDatabase("data")

# Push a local file to the database
db.push("ros1.bag")

# Check to make sure it is really there
ls = db.ls()
print(ls)
