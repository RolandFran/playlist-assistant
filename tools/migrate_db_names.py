import sqlite3

DB_PATH = "spotify_history.db"


def table_exists(conn, table_name):
    row = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name = ?
        """,
        (table_name,),
    ).fetchone()

    return row is not None


def column_exists(conn, table_name, column_name):
    columns = conn.execute(
        f"PRAGMA table_info({table_name})"
    ).fetchall()

    return any(
        column[1] == column_name
        for column in columns
    )


def main():
    with sqlite3.connect(DB_PATH) as conn:
        print()
        print("Starte DB-Migration...")
        print()

        #
        # source_playlists -> source
        #
        if table_exists(conn, "source_playlists"):
            if not table_exists(conn, "source"):
                conn.execute(
                    """
                    ALTER TABLE source_playlists
                    RENAME TO source
                    """
                )
                print(
                    "source_playlists -> source"
                )
            else:
                print(
                    "source existiert bereits."
                )

        #
        # playlist_tracks -> playlist
        #
        if table_exists(conn, "playlist_tracks"):
            if not table_exists(conn, "playlist"):
                conn.execute(
                    """
                    ALTER TABLE playlist_tracks
                    RENAME TO playlist
                    """
                )
                print(
                    "playlist_tracks -> playlist"
                )
            else:
                print(
                    "playlist existiert bereits."
                )

        #
        # plays -> history
        #
        if table_exists(conn, "plays"):
            if not table_exists(conn, "history"):
                conn.execute(
                    """
                    ALTER TABLE plays
                    RENAME TO history
                    """
                )
                print(
                    "plays -> history"
                )
            else:
                print(
                    "history existiert bereits."
                )

        #
        # history.source -> history.data_source
        #
        if table_exists(conn, "history"):
            if (
                column_exists(
                    conn,
                    "history",
                    "source",
                )
                and not column_exists(
                    conn,
                    "history",
                    "data_source",
                )
            ):
                conn.execute(
                    """
                    ALTER TABLE history
                    RENAME COLUMN source
                    TO data_source
                    """
                )

                print(
                    "history.source -> "
                    "history.data_source"
                )

        conn.commit()

        print()
        print("Aktuelle Tabellen:")
        print("-" * 50)

        tables = conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            ORDER BY name
            """
        ).fetchall()

        for table in tables:
            print(table[0])

        print()
        print("Migration abgeschlossen.")


if __name__ == "__main__":
    main()