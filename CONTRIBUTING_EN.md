# 🤝 Contributing

We welcome all contributions! Thank you for your interest in improving the Islamic Prayer Times Bot.

---

## 📋 How Can I Contribute?

There are several ways to contribute:

1. 🐛 **Report bugs** - Open an issue on GitHub
2. 💡 **Suggest features** - Share your ideas with us
3. 📖 **Improve documentation** - Help make README clearer
4. 🔧 **Fix bugs** - Submit a Pull Request for fixes
5. ✨ **Add features** - Help develop the bot

---

## 🚀 Getting Started with Development

### 1️⃣ Fork & Clone the Project

```bash
# Fork the repository from GitHub
git clone https://github.com/yourusername/islamic-prayer-bot.git
cd islamic-prayer-bot
```

### 2️⃣ Create a New Branch

```bash
git checkout -b feature/AmazingFeature
# or
git checkout -b fix/SomeBug
```

### 3️⃣ Install Dependencies

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

pip install -r requirements.txt
```

### 4️⃣ Make Changes

- Follow the existing code style
- Add docstrings for new functions
- Ensure code follows PEP 8
- Test your changes thoroughly

### 5️⃣ Run Tests

```bash
# Test database
python -c "from database import initialize_database; initialize_database()"

# Test category loading
python init_categories.py

# Run bot for testing
python bot.py
```

### 6️⃣ Commit Changes

```bash
git add .
git commit -m "Add some AmazingFeature: description here"
```

### 7️⃣ Push to Branch

```bash
git push origin feature/AmazingFeature
```

### 8️⃣ Open a Pull Request

1. Open a Pull Request on GitHub
2. Provide a clear description of your changes
3. Wait for review

---

## 📝 Coding Standards

### Code Style
- Follow **PEP 8** where possible
- Use 4 spaces for indentation (not tabs)
- Add docstrings for functions and classes
- Use clear, meaningful variable names

### Documentation
- Add docstrings for every new function
- Use Google style or NumPy style for docstrings
- Update CHANGELOG.md when adding major features

### Security
- Never commit tokens in code
- Use environment variables for sensitive settings
- Review code for security vulnerabilities

---

## 🐛 Reporting Issues

When opening an issue, please include:

- 📝 **Clear description** of the problem
- 💻 **Environment details**:
  - Python version
  - Operating system version
  - Bot version
- 📋 **Steps to reproduce**:
  - What did you do?
  - What did you expect?
  - What actually happened?
- 📄 **Logs**:
  - Attach `bot_debug.log` if possible
  - Remove any sensitive information from logs

### Good Issue Example:

```
## 🐛 Bug
Bot not sending azan notifications to some groups

## 💻 Environment
- Python: 3.10
- OS: Ubuntu 22.04
- Bot Version: v2.0.0

## 📋 Steps to Reproduce
1. Added bot to group
2. Used /setup
3. Selected city: Riyadh
4. Waited for Dhuhr prayer time
5. No notification received

## 📄 Logs
[attach bot_debug.log here]
```

---

## 💡 Feature Requests

When suggesting a new feature, please include:

- 📝 **Feature description** - What should it do?
- 🎯 **Benefit** - How will this help users?
- 💡 **Ideas** - How could it be implemented?

### Good Feature Request Example:

```
## 💡 Proposed Feature
Ability to set custom times for hadith sending

## 🎯 Benefit
Some groups prefer hadiths at different times than default windows

## 💡 Ideas
Could add `/sethadithtime` command for admins to set custom times per group
```

---

## 🎯 Pull Request Guidelines

### Before Opening a PR:
- ✅ Read [CONTRIBUTING.md](CONTRIBUTING.md)
- ✅ Added tests for your changes (if possible)
- ✅ Updated documentation (README, CHANGELOG)
- ✅ Code follows project standards
- ✅ Tested all major commands

### In PR Description:
- 📝 Clear description of changes
- 🔗 Link to related issue (if applicable)
- 📸 Screenshots for UI changes (if any)
- ✅ List of tests you ran

---

## 🏷️ Commit Naming Conventions

Use **Conventional Commits** format:

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, no logic change)
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `test`: Adding/updating tests
- `chore`: Other changes

### Examples:

```bash
git commit -m "feat(hadith): add time-based category selection"
git commit -m "fix(database): resolve connection leaks"
git commit -m "docs(readme): update installation guide"
git commit -m "perf(scheduler): replace polling with APScheduler"
```

---

## ❓ FAQ

### Q: Can I suggest a major feature?
A: Yes! Open an issue first to discuss before starting development.

### Q: What if I'm new to Python?
A: No problem! You can contribute by:
- Improving documentation
- Reporting bugs
- Suggesting features
- Translating documentation

### Q: Is there a roadmap for future features?
A: Yes! Check [CHANGELOG.md](CHANGELOG.md) - "Future Roadmap" section

---

## 🧧 Development Tools

### Testing
```bash
# Run bot
python bot.py

# Test database
python -c "from database import initialize_database; initialize_database()"

# Load categories
python init_categories.py
```

### Linting
```bash
# Use pylint (optional)
pip install pylint
pylint *.py
```

### Code Review
- Use GitHub's built-in review system
- Focus on: security, performance, correctness, documentation

---

## 📞 Contact

- 💬 Telegram: [Khaled](https://t.me/A245F)
- 🐛 Issues: [GitHub Issues](https://github.com/muslim-kh09/Islamic-Prayer-Times-Bot/issues)

---

<div align="center">

**Thank you for your contribution! ❤️**

</div>
