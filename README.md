# TagesschauTelegramBot
Share the current episode of Tagesschau/Tagesthemen with a quick inline command.

## Run

1. Copy crendentials.example.json to credentials.json.
```bash
cp crendentials.example.json credentials.json
```

2. Add you bot api key to credentials.json.

3. Install dependencies
```bash
pip install -r requirements.txt
```

4. Start the bot.
```bash
python bot.py
```


## Usage

```bash
@bot-name <keyword> <quality> <send-link>
```

|Argument     |Required|Explanation                          |Default           |Possible options                          |
|-------------|--------|-------------------------------------|------------------|------------------------------------------|
|keyword      |optional|Keyword identifying show             |all               |all, tagesschau, tagesthemen, tageschau100|
|quality      |optional|Quality of the video                 |depends on keyword|webs, webm, webl, webxl                   |
|send-link    |optional|Send a link instead of the video     |depends on keyword|True, False                               |


Notice that if the file is bigger than 20MB it can only be send with `send-link=True`.