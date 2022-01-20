# Bloo

## Setup instructions
These instructions assume you are on macOS or Linux. Windows users, good luck.

### With Docker (recommended!)
You will need the following installed:
- Docker
- Visual Studio Code to run the development container
- MongoDB running on the host machine or [MongoDB Atlas](https://www.mongodb.com/atlas/database).

#### Steps
1. Clone the repository and open the folder in Visual Studio Code
2. Install the [Microsoft Remote Development](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.vscode-remote-extensionpack) plugin
3. Make sure that Docker is running
4. Open the Command Palette (`CMD+Shift+P` or `CTRL+Shift+P`) and run "Remote-Containers: Reopen In Container"
5. VSCode should build the Docker image and open it automatically; this may take a couple of minutes as it has to install some extensions as well.
6. Set up the `.env` file as shown [here](#env-file).
7. Make sure the database is set up.
8. Open the integrated terminal in VSCode and run the `bloo` command to start the bot with hot reload!

> Note that if you make changes to the `Dockerfile`, `.devcontainer.json`, or need to install a new requirement, you need to rebuild the Docker image. You can do this through the Command Palette again, run "Remote-Containers: Rebuild Container".

### Without Docker (not recommended)
You will need the following installed:
- `python3.9+`
- `venv` (Python's virtualenv module)
- MongoDB running on the host machine or [MongoDB Atlas](https://www.mongodb.com/atlas/database).

#### Steps
1. Inside the root folder of the project, run `python3 -m venv venv/`
2. `source venv/bin/activate`
3. `pip3 install -r requirements.txt`
4. Set up the .env file as shown [here](#env-file).
5. Make sure the database is set up.
6. `python3 main.py`

## `.env` file

If not using Docker, you can change `DB_HOST` to `localhost` instead. `host.docker.internal` works on macOS and Windows, on Linux you can use `172.17.0.1`.

Optionally, you can use [MongoDB Atlas](https://www.mongodb.com/atlas/database) instead of a local Mongo server, or you can ask SlimShadyIAm on Discord for access to the shared test database. In that case, you use:
`DB_CONNECTION_STRING=mongodb+srv://.....` instead of `DB_HOST` and `DB_PORT`.

```
BLOO_TOKEN="your token here"

MAIN_GUILD_ID=12345
OWNER_ID=12345
AARON_ID=123 # ID of whoever owns the server

DB_HOST="host.docker.internal"
DB_PORT=27017

# this is optional, if you want ban appeal form support
BAN_APPEAL_URL=""
BAN_APPEAL_GUILD_ID=12345
BAN_APPEAL_MOD_ROLE=12345

# this is optional, set this for development
# (it's False by default for production)
DEV=True

# this is optional if you want logging to be sent to a Discord webhook
LOGGING_WEBHOOK_URL=""

# this is optional, for /sabbath command
AARON_ROLE=123

# used for automatically uploading tweak lists to paste.ee
PASTEE_TOKEN="your API key here"

# optional, for /neural_net meme command
RESNEXT_TOKEN="your token here"
```

## Contributors

<table>
  <tr>
    <td align="center"><a href="https://aamirfarooq.dev"><img src="https://avatars.githubusercontent.com/u/10660846?v=4" width="100px;" alt=""/><br /><sub><b>SlimShadyIAm</b></sub></a></td>
    <td align="center"><a href="https://github.com/stekc"><img src="https://avatars.githubusercontent.com/u/57512084?v=4" width="100px;" alt=""/><br /><sub><b>stekc</b></sub></a></td>
    <td align="center"><a href="https://github.com/Ultra03"><img src="https://avatars.githubusercontent.com/u/20672260?v=4" width="100px;" alt=""/><br /><sub><b>Ultra03</b></sub></a></td>
    <td align="center"><a href="https://github.com/ja1dan"><img src="https://avatars.githubusercontent.com/u/37126748?v=4" width="100px;" alt=""/><br /><sub><b>ja1dan</b></sub></a></td>
    <td align="center"><a href="https://github.com/donato-fiore"><img src="https://avatars.githubusercontent.com/u/50346119?v=4" width="100px;" alt=""/><br /><sub><b>donato-fiore</b></sub></a></td>
  </tr>
  <tr>
    <td align="center"><a href="https://m1sta.xyz/"><img src="https://avatars.githubusercontent.com/u/37033149?v=4" width="100px;" alt=""/><br /><sub><b>m1stadev</b></sub></a></td>
    <td align="center"><a href="https://saadat.dev/"><img src="https://avatars.githubusercontent.com/u/41216857?v=4" width="100px;" alt=""/><br /><sub><b>mass1ve-err0r</b></sub></a></td>
    <td align="center"><a href="https://github.com/sqlstatement"><img src="https://avatars.githubusercontent.com/u/27446425?v=4" width="100px;" alt=""/><br /><sub><b>sqlstatement</b></sub></a></td>
    <td align="center"><a href="https://github.com/beerpiss"><img src="https://avatars.githubusercontent.com/u/92439990?v=4" width="100px;" alt=""/><br /><sub><b>beerpsi</b></sub></a></td>
  </tr>
  </table>

### Special thanks
Special thanks to the following people for ideas, testing, or help:
- [Jack LaFond](https://www.jack.link/) --- creator of [tunes.ninja](https://tunes.ninja/), the bot that the Songs cog is inspired by
- Cameren from r/jb, who has given a lot of ideas and helped with testing on many occasions
- [Lillie](https://github.com/LillieWeeb001/) --- creator of the [fake jailbreak and iCloud bypass list](https://github.com/LillieWeeb001/Anti-Scam-Json-List) used by Bloo's filter
