# PROJECT BIBLE

> TRIP
> Tourism Resource Integration Platform

Version : 0.1.0

Status : Active Development

---

# 1. PROJECT OVERVIEW

Project Name

TRIP

Full Name

Village Insight Decision Support System

Purpose

Develop a web-based Decision Support System (DSS) that assists the government in evaluating, analyzing, and recommending tourism village development strategies based on statistical research.

---

# 2. RESEARCH FOUNDATION

Research Methods

- Path Analysis
- Principal Component Analysis (PCA)
- Cluster Analysis

Dataset

- 24 Tourism Villages
- 1,152 Respondents

Variables

Independent Variables

- X1
- X2
- X3
- X4
- X5

Mediator Variables

- Y1
- Y2
- Y3

Dependent Variables

- Y4
- Y5
- Y6

Research Outputs

- Path Coefficient
- PCA Components
- Cluster Labels
- Recommendation Basis

---

# 3. PROJECT GOALS

Primary Goals

- Questionnaire Management
- Village Assessment
- Data Visualization
- Cluster Prediction
- Recommendation Engine
- Decision Support

Secondary Goals

- Academic Research
- Government Monitoring
- Future Expansion
- Public Information

---

# 4. TECHNOLOGY STACK

Backend

- Python
- Django

Database

- PostgreSQL

Frontend

- HTML5
- Bootstrap 5
- JavaScript

Visualization

- Plotly
- Leaflet

Machine Learning

- Scikit-Learn
- Joblib
- Pandas
- NumPy

Deployment

- Docker
- Gunicorn
- Nginx

---

# 5. PROJECT STRUCTURE

VillageInsightDSS/

backend/

apps/

accounts/

villages/

variables/

indicators/

questionnaires/

surveys/

respondents/

analytics/

dashboard/

assessment/

recommendation/

reports/

administration/

audit/

config/

core/

common/

machine_learning/

media/

static/

templates/

manage.py

datasets/

deployment/

docs/

scripts/

tests/

---

# 6. SOFTWARE ARCHITECTURE

Browser

↓

URL

↓

View

↓

Service

↓

Repository

↓

Model

↓

PostgreSQL

Business Logic must NEVER be placed inside View.

---

# 7. DESIGN PRINCIPLES

Always follow

- SOLID
- DRY
- KISS
- Clean Architecture
- Separation of Concerns
- Reusable Components

---

# 8. DJANGO APPLICATIONS

accounts

Authentication

villages

Village Management

variables

Research Variables

indicators

Research Indicators

questionnaires

Question Bank

respondents

Respondent Management

surveys

Survey Management

analytics

Analytics Engine

dashboard

Dashboard

assessment

Assessment Engine

recommendation

Recommendation Engine

reports

Reporting

administration

Administration

audit

Audit Log

---

# 9. DATABASE LAYERS

System

Master

Research

Transaction

Analytics

Logging

---

# 10. MASTER TABLES

mst_village

mst_variable

mst_indicator

mst_question

mst_cluster

mst_region

---

# 11. TRANSACTION TABLES

trx_survey

trx_respondent

trx_answer

trx_variable_score

trx_prediction

trx_recommendation

---

# 12. MACHINE LEARNING

Artifacts

- scaler.pkl
- pca.pkl
- cluster.pkl

Rules

- cluster_rules.json
- recommendation_rules.json

---

# 13. USER ROLES

Administrator

Operator

Researcher

Government

Guest

---

# 14. CODING RULES

Python

snake_case

Classes

PascalCase

Constants

UPPER_CASE

HTML

kebab-case

URLs

lowercase

---

# 15. GIT STRATEGY

main

Production

develop

Development

feature/*

New Features

fix/*

Bug Fixes

---

# 16. VERSIONING

Major.Minor.Patch

Example

0.1.0

---

# 17. DEVELOPMENT PHASES

Phase 0

Architecture

Phase 1

Foundation

Phase 2

Master Data

Phase 3

Survey

Phase 4

Dashboard

Phase 5

Analytics

Phase 6

Machine Learning

Phase 7

Recommendation

Phase 8

Reporting

Phase 9

Deployment

---

# 18. PROJECT RULES

- Never place business logic in views.
- Always use Service Layer.
- Always use Repository Layer.
- Never duplicate code.
- Keep modules independent.
- Follow enterprise architecture.
- Maintain documentation with every sprint.
- Write clean, readable, and maintainable code.

---

# 19. LONG-TERM GOALS

- Explainable AI
- GIS Integration
- REST API
- Mobile Support
- Multi-Year Analytics
- Public Dashboard
- Real-Time Assessment

---

# 20. DYNAMIC VARIABLE MODELING

Predictor / Mediator / Response dikonfigurasi secara dinamis (bukan
hard-coded). Variable punya `role`, `order`, dan `mediator_layer`.

Mapping

- Predictor -> X1...Xn
- Mediator  -> Y1...Yn (0..N layer)
- Response  -> Z1...Zn

Code X/Y/Z adalah display code (bukan primary key). Primary key = `id`.
Urutan persistis lewat `order`; layer mediator lewat model
`MediatorLayer`. Source of truth = `VariableConfigurationService`.

Lihat: docs/architecture/dynamic-variable-modeling.md

# END OF PROJECT BIBLE