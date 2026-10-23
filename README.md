\# GoldApple — Beauty \& Wellness Data Analytics



\## Overview



An end-to-end Python project focused on collecting, storing, analyzing, and serving beauty and wellness product data from GoldApple.



The project covers three product categories:

\- Perfumes

\- Skincare

\- Supplements



The dataset contains approximately \*\*1,470 unique products\*\*, including prices, brands, ratings, customer reviews, and category-specific attributes.



\## Tech Stack



\- \*\*Python\*\* — data collection and processing

\- \*\*Playwright / asyncio\*\* — asynchronous web scraping

\- \*\*PostgreSQL\*\* — relational data storage

\- \*\*SQL\*\* — analytical queries and window functions

\- \*\*pandas / Matplotlib\*\* — exploratory and business analysis

\- \*\*FastAPI / Uvicorn\*\* — REST API

\- \*\*Docker / Docker Compose\*\* — containerized API and database



\## Project Architecture



```text

GoldApple Catalog

&#x20;      |

&#x20;      v

Python + Playwright

&#x20;      |

&#x20;      v

PostgreSQL

&#x20;      |

&#x20;      +---- SQL Analytics

&#x20;      |

&#x20;      +---- pandas Business Analysis

&#x20;      |

&#x20;      +---- FastAPI REST API

&#x20;                   |

&#x20;                   v

&#x20;              Docker Compose

```



\## Database



The relational database consists of four tables:



\- `product` — shared product information and customer feedback

\- `perfume` — fragrance groups, notes, and volume

\- `skincare` — skin types, intended uses, ingredients, and other attributes

\- `supplement` — ingredients, intended uses, release forms, and other attributes



Tables are linked through `item\_id`. Some products belong to more than one specialized category.



\## Analytics



\*\*Business Case 1 — Brand Analysis\*\*



Identifying skincare brands with consistent customer-review activity and positive recommendation signals.



\*\*Business Case 2 — Perfume Recommendations\*\*



An experimental, rule-based product similarity algorithm using fragrance notes and fragrance groups. No machine learning model is used.



\*\*SQL Analytics\*\*



Five exercises covering pricing segmentation, brand aggregation, category metrics, window functions, and overlapping product categories.



\## REST API



The FastAPI service supports:



\- `GET /health` — health check

\- `GET /products` — retrieve products with optional filters

\- `GET /products/{item\_id}` — retrieve a specific product

\- `GET /docs` — interactive API documentation



\## Running the API



Requirements: Docker Desktop and Docker Compose.



Create a local `.env` file based on `.env.example` and configure the PostgreSQL password.



The current Compose configuration also requires a local `init.sql` containing the database schema and initial data.



```bash

docker compose up --build -d

```



API documentation:



`http://localhost:8001/docs`



Stop containers:



```bash

docker compose down

```



\## Limitations



\- Customer reviews are not equivalent to product sales.

\- Product prices and attributes represent a collected snapshot.

\- The perfume recommendation algorithm is a rule-based prototype, not a validated production recommender.

\- Data completeness depends on the source website and collection process.



\## Project Goal



Demonstrate practical skills across the data workflow:



\*\*Data Collection → Database → SQL → pandas Analysis → API → Containerization\*\*

