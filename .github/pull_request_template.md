## Summary

- 

## Scope

Select all that apply:

- [ ] CLI
- [ ] Web UI
- [ ] Agent Skill
- [ ] Core search logic
- [ ] Source adapter
- [ ] Deployment
- [ ] Documentation
- [ ] Tests only

## Tests

List the checks you ran:

- [ ] `python -m compileall -q paperseek skills/paperseek/scripts`
- [ ] `python -m unittest discover -s tests`
- [ ] `python -m pytest -q`
- [ ] `node --check paperseek/static/app.js`
- [ ] Manual smoke test:

## Notes

- Breaking changes:
- API-provider assumptions:
- Known limitations:

## Safety

- [ ] I did not commit API keys, tokens, cookies, private search history, or protected full-text content.
- [ ] This change does not add paywall bypass, credential sharing, or bulk protected PDF downloading.
