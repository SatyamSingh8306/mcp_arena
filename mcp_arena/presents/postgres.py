from mcp.server.fastmcp import FastMCP
from typing import Literal, Annotated, Optional, List, Dict, Any, Union
from datetime import datetime, date
from dataclasses import dataclass, asdict, field
from enum import Enum
import psycopg2
from psycopg2 import sql
from psycopg2.extras import RealDictCursor
import os

@dataclass
class TableInfo:
    table_name: str
    table_schema: str
    table_type: str
    row_count: Optional[int]
    size_bytes: Optional[int]
    comment: Optional[str]

@dataclass
class ColumnInfo:
    column_name: str
    data_type: str
    is_nullable: bool
    column_default: Optional[str]
    character_maximum_length: Optional[int]
    numeric_precision: Optional[int]
    numeric_scale: Optional[int]
    is_primary_key: bool
    is_foreign_key: bool
    comment: Optional[str]

@dataclass
class QueryResult:
    columns: List[str]
    rows: List[Dict[str, Any]]
    row_count: int
    execution_time: float

from mcp_arena.mcp.server import BaseMCPServer

class PostgresMCPServer(BaseMCPServer):
    """PostgreSQL MCP Server for interacting with PostgreSQL databases."""
    
    def __init__(
        self,
        connection_string: Optional[str] = None,
        host: str = "127.0.0.1",
        port: int = 8000,
        transport: Literal['stdio', 'sse', 'streamable-http'] = "stdio",
        debug: bool = False,
        auto_register_tools: bool = True,
        **base_kwargs
    ):
        """Initialize PostgreSQL MCP Server.
        
        Args:
            connection_string: PostgreSQL connection string. If not provided, will try to get from POSTGRES_CONNECTION_STRING env var.
            host: Host to run server on
            port: Port to run server on
            transport: Transport type
            debug: Enable debug mode
            auto_register_tools: Automatically register tools on initialization
            **base_kwargs: Additional arguments for BaseMCPServer
        """
        self.connection_string = connection_string or os.getenv("POSTGRES_CONNECTION_STRING")
        if not self.connection_string:
            raise ValueError(
                "PostgreSQL connection string is required. "
                "Provide it as argument or set POSTGRES_CONNECTION_STRING environment variable."
            )
        
        super().__init__(
            name="PostgreSQL MCP Server",
            description="MCP server for interacting with PostgreSQL databases.",
            host=host,
            port=port,
            transport=transport,
            debug=debug,
            auto_register_tools=auto_register_tools,
            **base_kwargs
        )
    
    def _register_tools(self) -> None:
        """Register all PostgreSQL-related tools."""
        self._register_connection_tools()
        self._register_schema_tools()
        # self._register_table_tools()
        self._register_query_tools()
        # self._register_user_tools()
        # self._register_index_tools()

    def _get_connection(self):
        """Get a database connection"""
        return psycopg2.connect(self.connection_string)

    def _register_connection_tools(self):
        @self.mcp_server.tool()
        def test_connection() -> Dict[str, Any]:
            """Test PostgreSQL connection"""
            try:
                conn = self._get_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT version()")
                version = cursor.fetchone()[0]
                cursor.execute("SELECT current_database()")
                db_name = cursor.fetchone()[0]
                cursor.close()
                conn.close()
                
                return {
                    "success": True,
                    "version": version,
                    "database": db_name,
                    "status": "Connected successfully"
                }
            except Exception as e:
                return {"error": f"Connection failed: {str(e)}"}

    def _register_schema_tools(self):
        @self.mcp_server.tool()
        def list_tables(
            schema: Annotated[Optional[str], "Schema name"] = "public"
        ) -> Dict[str, Any]:
            """List all tables in a schema"""
            try:
                conn = self._get_connection()
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                
                query = """
                SELECT 
                    table_name,
                    table_schema,
                    table_type,
                    (SELECT count(*) FROM information_schema.tables t2 
                     WHERE t2.table_schema = t.table_schema) as row_count_estimate
                FROM information_schema.tables t
                WHERE table_schema = %s
                ORDER BY table_name
                """
                
                cursor.execute(query, (schema,))
                tables = cursor.fetchall()
                
                result = []
                for table in tables:
                    table_info = TableInfo(
                        table_name=table["table_name"],
                        table_schema=table["table_schema"],
                        table_type=table["table_type"],
                        row_count=table.get("row_count_estimate"),
                        size_bytes=None,
                        comment=None
                    )
                    result.append(asdict(table_info))
                
                cursor.close()
                conn.close()
                
                return {"tables": result, "count": len(result)}
            except Exception as e:
                return {"error": f"Failed to list tables: {str(e)}"}

        @self.mcp_server.tool()
        def get_table_schema(
            table_name: Annotated[str, "Table name"],
            schema: Annotated[Optional[str], "Schema name"] = "public"
        ) -> Dict[str, Any]:
            """Get schema information for a table"""
            try:
                conn = self._get_connection()
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                
                # Get column information
                columns_query = """
                SELECT 
                    c.column_name,
                    c.data_type,
                    c.is_nullable,
                    c.column_default,
                    c.character_maximum_length,
                    c.numeric_precision,
                    c.numeric_scale,
                    CASE WHEN kcu.column_name IS NOT NULL THEN true ELSE false END as is_primary_key,
                    CASE WHEN fk.constraint_name IS NOT NULL THEN true ELSE false END as is_foreign_key,
                    pgd.description as comment
                FROM information_schema.columns c
                LEFT JOIN information_schema.key_column_usage kcu
                    ON c.table_schema = kcu.table_schema 
                    AND c.table_name = kcu.table_name 
                    AND c.column_name = kcu.column_name
                    AND kcu.constraint_name IN (
                        SELECT constraint_name 
                        FROM information_schema.table_constraints 
                        WHERE constraint_type = 'PRIMARY KEY'
                    )
                LEFT JOIN information_schema.constraint_column_usage ccu
                    ON c.table_schema = ccu.table_schema 
                    AND c.table_name = ccu.table_name 
                    AND c.column_name = ccu.column_name
                LEFT JOIN (
                    SELECT 
                        tc.constraint_name,
                        kcu.column_name,
                        ccu.table_name as foreign_table_name,
                        ccu.column_name as foreign_column_name
                    FROM information_schema.table_constraints tc
                    JOIN information_schema.key_column_usage kcu
                        ON tc.constraint_name = kcu.constraint_name
                    JOIN information_schema.constraint_column_usage ccu
                        ON tc.constraint_name = ccu.constraint_name
                    WHERE tc.constraint_type = 'FOREIGN KEY'
                ) fk ON c.column_name = fk.column_name 
                    AND c.table_name = fk.table_name
                LEFT JOIN pg_catalog.pg_statio_all_tables st
                    ON c.table_schema = st.schemaname 
                    AND c.table_name = st.relname
                LEFT JOIN pg_catalog.pg_description pgd
                    ON pgd.objoid = st.relid 
                    AND pgd.objsubid = c.ordinal_position
                WHERE c.table_schema = %s AND c.table_name = %s
                ORDER BY c.ordinal_position
                """
                
                cursor.execute(columns_query, (schema, table_name))
                columns = cursor.fetchall()
                
                result = []
                for col in columns:
                    col_info = ColumnInfo(
                        column_name=col["column_name"],
                        data_type=col["data_type"],
                        is_nullable=col["is_nullable"] == "YES",
                        column_default=col["column_default"],
                        character_maximum_length=col["character_maximum_length"],
                        numeric_precision=col["numeric_precision"],
                        numeric_scale=col["numeric_scale"],
                        is_primary_key=col["is_primary_key"],
                        is_foreign_key=col["is_foreign_key"],
                        comment=col["comment"]
                    )
                    result.append(asdict(col_info))
                
                # Get table constraints
                constraints_query = """
                SELECT 
                    constraint_name,
                    constraint_type,
                    check_clause
                FROM information_schema.table_constraints
                WHERE table_schema = %s AND table_name = %s
                """
                
                cursor.execute(constraints_query, (schema, table_name))
                constraints = cursor.fetchall()
                
                cursor.close()
                conn.close()
                
                return {
                    "table_name": table_name,
                    "schema": schema,
                    "columns": result,
                    "constraints": constraints,
                    "column_count": len(result)
                }
            except Exception as e:
                return {"error": f"Failed to get table schema: {str(e)}"}

    def _register_query_tools(self):
        @self.mcp_server.tool()
        def execute_query(
            query: Annotated[str, "SQL query to execute"],
            params: Annotated[Optional[Dict], "Query parameters"] = None
        ) -> Dict[str, Any]:
            """Execute a SQL query"""
            import time
            try:
                conn = self._get_connection()
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                
                start_time = time.time()
                
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                
                execution_time = time.time() - start_time
                
                if cursor.description:
                    columns = [desc[0] for desc in cursor.description]
                    rows = cursor.fetchall()
                    row_count = len(rows)
                else:
                    columns = []
                    rows = []
                    row_count = cursor.rowcount
                    conn.commit()
                
                result = QueryResult(
                    columns=columns,
                    rows=rows,
                    row_count=row_count,
                    execution_time=execution_time
                )
                
                cursor.close()
                conn.close()
                
                return asdict(result)
            except Exception as e:
                return {"error": f"Query failed: {str(e)}"}