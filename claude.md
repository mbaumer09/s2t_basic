# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with this repository.

## Important
- ALL instructions within this document MUST BE FOLLOWED, these are not optional unless explicitly stated.
- DO NOT edit more code than you have to.
- DO NOT WASTE TOKENS, be succinct and concise.

### Coding Overview

- Review the PRD `docs/prd.txt` if you are not sure about the goals of any work you are on.
- Explain your approach step-by-step before writing any code.


### SOLID Principles

- Single Responsibility Principle: A class or function should have one purpose only.
- Open/Closed Principle: Classes should be open for extension but closed for modification.
- Liskov Substitution Principle: Imagine a function that expects a Bird. You should be able to pass in a Sparrow or a Duck, and it should just work.
- Interface Segregation Principle: Don't make a big, fat interface with a bunch of unrelated methods. Instead, split large interfaces into smaller, more specific ones so that classes only implement what they actually need.
- Dependency Inversion Principle: A design rule that says high-level code should depend on abstractions, not concrete implementations.

