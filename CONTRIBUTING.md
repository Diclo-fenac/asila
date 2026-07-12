# Contributing to Asila

First off, thank you for considering contributing to Asila! It's people like you that make Asila such a great tool for government-scale verified information management.

## 1. Where do I go from here?

If you've noticed a bug or have a feature request, make sure to check our [Issues](../../issues) to see if someone else in the community has already created a ticket. If not, go ahead and make one!

## 2. Fork & create a branch

If this is something you think you can fix, then fork Asila and create a branch with a descriptive name.

## 3. Get the test suite running

Make sure you have the prerequisites installed:
* Python 3.11+
* Node.js 18+
* Docker & Docker Compose
* `uv` for python dependencies

Run the test suite to ensure your baseline is clean:
```bash
uv run pytest tests/
```

## 4. Implement your fix or feature

At this point, you're ready to make your changes! Feel free to ask for help; everyone is a beginner at first.

## 5. Make a Pull Request

At this point, you should switch back to your master branch and make sure it's up to date with Asila's master branch:

```bash
git remote add upstream git@github.com:Diclo-fenac/asila.git
git checkout master
git pull upstream master
```

Then update your feature branch from your local copy of master, and push it!

```bash
git checkout <branch-name>
git rebase master
git push --set-upstream origin <branch-name>
```

Finally, go to GitHub and make a Pull Request.

## Coding Style

*   **Python**: We use `black` and `ruff` for formatting and linting.
*   **TypeScript**: We use `eslint` and `prettier`. 

Run the formatters before submitting your PR to ensure the CI passes!
