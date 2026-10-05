from __future__ import annotations

from typing import Any

import streamlit as st
from neo4j import GraphDatabase, RoutingControl


# =========================================================
# NEO4J CONFIG
# =========================================================

def _config() -> tuple[str, str, str, str]:
    cfg = st.secrets["neo4j"]

    return (
        cfg["uri"],
        cfg["username"],
        cfg["password"],
        cfg.get("database", "neo4j"),
    )


# =========================================================
# NEO4J DRIVER
# =========================================================

@st.cache_resource(show_spinner=False)
def get_driver():
    """Create one thread-safe Neo4j Driver for the Streamlit process."""

    uri, username, password, _ = _config()

    driver = GraphDatabase.driver(
        uri,
        auth=(username, password)
    )

    driver.verify_connectivity()

    return driver


# =========================================================
# QUERY
# =========================================================

def query(
    cypher: str,
    parameters: dict[str, Any] | None = None,
    *,
    write: bool = False
) -> list[dict[str, Any]]:

    _, _, _, database = _config()

    records, _, _ = get_driver().execute_query(
        cypher,
        parameters_=parameters or {},
        database_=database,
        routing_=(
            RoutingControl.WRITE
            if write
            else RoutingControl.READ
        ),
    )

    return [
        record.data()
        for record in records
    ]


# =========================================================
# PING
# =========================================================

def ping() -> bool:

    rows = query(
        "RETURN 1 AS ok"
    )

    return bool(
        rows and rows[0]["ok"] == 1
    )


# =========================================================
# CREATE SCHEMA
# =========================================================

def create_schema() -> None:

    statements = [

        """
        CREATE CONSTRAINT person_id_unique
        IF NOT EXISTS
        FOR (p:Person)
        REQUIRE p.person_id IS UNIQUE
        """,

        """
        CREATE CONSTRAINT pet_id_unique
        IF NOT EXISTS
        FOR (p:Pet)
        REQUIRE p.pet_id IS UNIQUE
        """,

    ]

    for stmt in statements:

        query(
            stmt,
            write=True
        )


# =========================================================
# SEED DEMO DATA
# =========================================================

def seed_demo_data() -> None:
    """
    Create sample Pet Recommendation graph.

    Person
    Pet
    FRIEND_OF
    HAS_PET
    """

    create_schema()

    # -----------------------------------------------------
    # PEOPLE
    # -----------------------------------------------------

    people = [

        {
            "person_id": "P001",
            "name": "June",
        },

        {
            "person_id": "P002",
            "name": "Beam",
        },

        {
            "person_id": "P003",
            "name": "Mew",
        },

        {
            "person_id": "P004",
            "name": "Ploy",
        },

        {
            "person_id": "P005",
            "name": "Ton",
        },

        {
            "person_id": "P006",
            "name": "Fai",
        },

    ]

    query(
        """
        UNWIND $rows AS row

        MERGE (
            p:Person {
                person_id: row.person_id
            }
        )

        SET p.name = row.name
        """,

        {
            "rows": people
        },

        write=True,
    )

    # -----------------------------------------------------
    # PETS
    # -----------------------------------------------------

    pets = [

        {
            "pet_id": "PET001",
            "name": "Dog",
        },

        {
            "pet_id": "PET002",
            "name": "Cat",
        },

        {
            "pet_id": "PET003",
            "name": "Rabbit",
        },

        {
            "pet_id": "PET004",
            "name": "Bird",
        },

        {
            "pet_id": "PET005",
            "name": "Fish",
        },

        {
            "pet_id": "PET006",
            "name": "Hamster",
        },

    ]

    query(
        """
        UNWIND $rows AS row

        MERGE (
            p:Pet {
                pet_id: row.pet_id
            }
        )

        SET p.name = row.name
        """,

        {
            "rows": pets
        },

        write=True,
    )

    # -----------------------------------------------------
    # FRIENDSHIPS
    # -----------------------------------------------------

    friendships = [

        ["P001", "P002"],  # June - Beam
        ["P001", "P003"],  # June - Mew
        ["P001", "P004"],  # June - Ploy

        ["P002", "P005"],  # Beam - Ton
        ["P003", "P006"],  # Mew - Fai

    ]

    query(
        """
        UNWIND $rows AS row

        MATCH
            (a:Person {
                person_id: row[0]
            }),

            (b:Person {
                person_id: row[1]
            })

        MERGE
            (a)-[:FRIEND_OF]->(b)

        MERGE
            (b)-[:FRIEND_OF]->(a)
        """,

        {
            "rows": friendships
        },

        write=True,
    )

    # -----------------------------------------------------
    # PET OWNERSHIP
    # -----------------------------------------------------

    pet_ownership = [

        ["P001", "PET001"],  # June -> Dog

        ["P002", "PET002"],  # Beam -> Cat
        ["P002", "PET003"],  # Beam -> Rabbit

        ["P003", "PET002"],  # Mew -> Cat
        ["P003", "PET004"],  # Mew -> Bird

        ["P004", "PET002"],  # Ploy -> Cat
        ["P004", "PET005"],  # Ploy -> Fish

        ["P005", "PET006"],  # Ton -> Hamster

        ["P006", "PET003"],  # Fai -> Rabbit

    ]

    query(
        """
        UNWIND $rows AS row

        MATCH
            (person:Person {
                person_id: row[0]
            }),

            (pet:Pet {
                pet_id: row[1]
            })

        MERGE
            (person)-[:HAS_PET]->(pet)
        """,

        {
            "rows": pet_ownership
        },

        write=True,
    )


# =========================================================
# GET PEOPLE
# =========================================================

def get_people() -> list[dict[str, Any]]:

    return query(
        """
        MATCH (p:Person)

        RETURN
            p.person_id AS person_id,
            p.name AS name

        ORDER BY p.person_id
        """
    )


# =========================================================
# DASHBOARD METRICS
# =========================================================

def get_dashboard_metrics() -> dict[str, int]:

    rows = query(
        """
        MATCH (p:Person)
        WITH count(p) AS people

        MATCH (pet:Pet)
        WITH people, count(pet) AS pets

        MATCH ()-[hp:HAS_PET]->()
        WITH
            people,
            pets,
            count(hp) AS has_pets

        MATCH ()-[f:FRIEND_OF]->()

        RETURN
            people,
            pets,
            has_pets,
            count(f) AS friendships
        """
    )

    return (
        rows[0]
        if rows
        else {
            "people": 0,
            "pets": 0,
            "has_pets": 0,
            "friendships": 0,
        }
    )


# =========================================================
# GET PROFILE
# =========================================================

def get_profile(
    person_id: str
) -> dict[str, Any] | None:

    rows = query(
        """
        MATCH (
            p:Person {
                person_id: $person_id
            }
        )

        OPTIONAL MATCH
            (p)-[:HAS_PET]->(pet:Pet)

        OPTIONAL MATCH
            (p)-[:FRIEND_OF]-(friend:Person)

        RETURN
            p.person_id AS person_id,
            p.name AS name,

            collect(
                DISTINCT pet.name
            ) AS pets,

            collect(
                DISTINCT friend.name
            ) AS friends
        """,

        {
            "person_id": person_id
        },
    )

    if not rows:

        return None

    row = rows[0]

    row["pets"] = [
        x
        for x in row.get("pets", [])
        if x
    ]

    row["friends"] = [
        x
        for x in row.get("friends", [])
        if x
    ]

    return row


# =========================================================
# PET RECOMMENDATION
# =========================================================

def recommend_pet(
    person_id: str
) -> list[dict[str, Any]]:
    """
    Recommend pets based on pets owned by friends.

    A pet already owned by the person
    will not be recommended.

    Score =
    number of friends who own that pet.
    """

    return query(
        """
        MATCH
            (
                person:Person {
                    person_id: $person_id
                }
            )

        MATCH
            (person)-[:FRIEND_OF]-(friend:Person)
            -[:HAS_PET]->(pet:Pet)

        WHERE NOT
            (
                person
            )-[:HAS_PET]->(pet)

        WITH
            pet,
            count(
                DISTINCT friend
            ) AS friend_score

        RETURN
            pet.name AS pet,
            friend_score AS score

        ORDER BY
            score DESC,
            pet
        """
        ,

        {
            "person_id": person_id
        },
    )


# =========================================================
# GRAPH NEIGHBORHOOD
# =========================================================

def graph_neighborhood(
    person_id: str,
    limit: int = 40
) -> list[dict[str, Any]]:

    return query(
        """
        MATCH
            (
                u:Person {
                    person_id: $person_id
                }
            )

        OPTIONAL MATCH
            p=(
                u
                )-[
                    :FRIEND_OF|HAS_PET
                *1..2
            ]-(x)

        WITH
            u,
            collect(p)[0..$limit] AS paths

        UNWIND paths AS p

        UNWIND relationships(p) AS r

        WITH DISTINCT
            startNode(r) AS s,
            r,
            endNode(r) AS t

        RETURN
            elementId(s) AS source_id,
            labels(s)[0] AS source_label,

            coalesce(
                s.name,
                s.person_id,
                s.pet_id
            ) AS source_name,

            type(r) AS relationship,

            elementId(t) AS target_id,
            labels(t)[0] AS target_label,

            coalesce(
                t.name,
                t.person_id,
                t.pet_id
            ) AS target_name

        LIMIT $limit
        """,

        {
            "person_id": person_id,
            "limit": int(limit)
        },
    )