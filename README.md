# Hypixel Guild Manager Bot

This is a Discord bot for managing Hypixel guild requirements.  
It checks **Bedwars Wins** and **Weekly GEXP** for guild members using the [Hypixel API](https://api.hypixel.net/).

---

## 📌 Features
- `/guildcheck [sort=bedwars|gexp]`
  - Displays all guild members with stats in an embed.
  - Sorted by either **Bedwars Wins** or **GEXP**.
  - Uses circle system:
    - 🟢 Meets both requirements
    - 🟡 Meets one requirement
    - 🔴 Meets none

- `/reqcheck {username}`
  - Displays an individual player's requirement check in an embed.

- Restricts usage to staff role only.

