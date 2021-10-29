# GIR

## Setup instructions
These instructions assume you are on macOS or Linux. Windows users, good luck.

### With Docker (recommended!)
You will need the following installed:
- Docker
- Visual Studio Code to run the development container
- MongoDB running on the host machine.

#### Steps
1. Clone the repository and open the folder in Visual Studio Code
2. Install the [Microsoft Remote Development](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.vscode-remote-extensionpack) plugin
3. Make sure that Docker is running
4. Open the Command Pallette (`CMD+Shift+P` or `CTRL+Shift+P`) and run "Remote-Containers: Reopen In Container"
5. VSCode should build the Docker image and open it automatically; this may take a couple of minutes as it has to install some extensions as well.
6. Set up the `.env` file as shown [here](#env-file).
7. Make sure the database is set up.
8. Open the integrated terminal in VSCode and run the `gir` command to start the bot with hot reload!

> Note that if you make changes to the `Dockerfile`, `.devcontainer.json`, or need to install a new requirement, you need to rebuild the Docker image. You can do this through the Command Pallette again, run "Remote-Containers: Rebuild Container".

### Without Docker (not recommended)
You will need the following installed:
- `python3.9+`
- `venv` (Python's virtualenv module)
- MongoDB

#### Steps
1. Inside the root folder of the project, run `python3 -m venv venv/`
2. `source venv/bin/activate`
3. `pip3 install -r requirements.txt`
4. Set up the .env file as shown [here](#env-file).
5. Make sure the database is set up.
6. `python3 main.py`

## `.env` file

If not using Docker, you can change `DB_HOST` to `localhost` instead. `host.docker.internal` works on macOS and Windows, on Linux you can use `172.17.0.1`.

```
GIR_TOKEN="your token here"

MAIN_GUILD_ID=12345
OWNER_ID=12345

DB_HOST="host.docker.internal"
DB_PORT=27017
```
