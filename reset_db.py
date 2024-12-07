import os
import shutil

# Remove the instance directory if it exists
if os.path.exists('instance'):
    shutil.rmtree('instance')

print("Database reset successful!")
