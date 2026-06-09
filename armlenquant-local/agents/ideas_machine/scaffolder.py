"""
Project Scaffolder
Generates project structure and files.
"""
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple
from loguru import logger
import json
import re

from poller.config import get_settings
from .models import (
    IdeaAnalysis, TechStackRecommendation, ProjectArchitecture,
    ProjectScaffold, ProjectType
)

settings = get_settings()


class ProjectScaffolder:
    """
    Generates project scaffolds with files and documentation.
    """
    
    def __init__(self):
        self.logger = logger.bind(component="scaffolder")
        self.output_path = Path(settings.projects_path)
        self.output_path.mkdir(parents=True, exist_ok=True)
    
    def scaffold(
        self,
        analysis: IdeaAnalysis,
        tech_stack: TechStackRecommendation,
        architecture: ProjectArchitecture
    ) -> ProjectScaffold:
        """
        Generate complete project scaffold.
        """
        self.logger.info(f"Scaffolding project: {analysis.title}")
        
        # Create project directory
        project_name = self._sanitize_name(analysis.title)
        project_path = self.output_path / project_name
        project_path.mkdir(parents=True, exist_ok=True)
        
        # Handle both enum and string values
        project_type = analysis.project_type
        if isinstance(project_type, str):
            project_type = ProjectType(project_type)
        
        # Get appropriate structure
        if analysis.is_fullstack:
            directories, files = self._scaffold_fullstack(analysis, tech_stack)
        elif project_type == ProjectType.WEB_APP:
            directories, files = self._scaffold_nextjs(analysis, tech_stack)
        elif project_type == ProjectType.API_SERVICE:
            directories, files = self._scaffold_fastapi(analysis, tech_stack)
        elif project_type == ProjectType.CLI_TOOL:
            directories, files = self._scaffold_cli(analysis, tech_stack)
        else:
            directories, files = self._scaffold_generic(analysis, tech_stack)
        
        # Create directories
        for dir_path in directories:
            (project_path / dir_path).mkdir(parents=True, exist_ok=True)
        
        # Create files
        for file_info in files:
            file_path = project_path / file_info["path"]
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(file_info["content"], encoding="utf-8")
        
        # Generate documentation
        docs = self._generate_documentation(analysis, tech_stack, architecture)
        docs_path = project_path / "docs"
        docs_path.mkdir(exist_ok=True)
        
        for doc_name, content in docs.items():
            (docs_path / doc_name).write_text(content, encoding="utf-8")
        
        # Generate Cursor prompts
        prompts = self._generate_cursor_prompts(analysis, tech_stack)
        prompts_path = project_path / "prompts"
        prompts_path.mkdir(exist_ok=True)
        
        for prompt_info in prompts:
            (prompts_path / prompt_info["filename"]).write_text(
                prompt_info["content"], encoding="utf-8"
            )
        
        # Generate .cursorrules
        cursorrules = self._generate_cursorrules(analysis, tech_stack)
        (project_path / ".cursorrules").write_text(cursorrules, encoding="utf-8")
        
        # Generate README
        readme = self._generate_readme(analysis, tech_stack, architecture)
        (project_path / "README.md").write_text(readme, encoding="utf-8")
        
        self.logger.info(f"Project scaffolded at: {project_path}")
        
        return ProjectScaffold(
            project_name=project_name,
            project_path=str(project_path),
            directories=directories,
            files=files,
            documentation=docs,
            prompts=prompts,
            created_at=datetime.utcnow()
        )
    
    def _sanitize_name(self, name: str) -> str:
        """Sanitize project name for filesystem."""
        # Remove special characters, replace spaces with underscores
        sanitized = re.sub(r'[^\w\s-]', '', name)
        sanitized = re.sub(r'[\s]+', '_', sanitized)
        sanitized = sanitized.lower()
        # Strip leading/trailing underscores
        sanitized = sanitized.strip('_')
        return sanitized
    
    def _scaffold_nextjs(
        self,
        analysis: IdeaAnalysis,
        tech_stack: TechStackRecommendation
    ) -> Tuple[List[str], List[Dict]]:
        """Scaffold Next.js project structure."""
        
        directories = [
            "src/app",
            "src/app/(auth)",
            "src/app/(dashboard)",
            "src/app/api",
            "src/components/ui",
            "src/components/features",
            "src/lib",
            "src/hooks",
            "src/stores",
            "src/types",
            "public/images",
            "docs",
            "prompts"
        ]
        
        files = [
            {
                "path": "package.json",
                "content": self._generate_package_json(analysis)
            },
            {
                "path": "tsconfig.json",
                "content": self._generate_tsconfig()
            },
            {
                "path": ".env.example",
                "content": self._generate_env_example(tech_stack)
            },
            {
                "path": ".gitignore",
                "content": self._generate_gitignore()
            },
            {
                "path": "src/app/layout.tsx",
                "content": self._generate_layout(analysis)
            },
            {
                "path": "src/app/page.tsx",
                "content": self._generate_homepage(analysis)
            },
            {
                "path": "src/lib/utils.ts",
                "content": 'import { type ClassValue, clsx } from "clsx";\nimport { twMerge } from "tailwind-merge";\n\nexport function cn(...inputs: ClassValue[]) {\n  return twMerge(clsx(inputs));\n}'
            }
        ]
        
        return directories, files
    
    def _scaffold_fastapi(
        self,
        analysis: IdeaAnalysis,
        tech_stack: TechStackRecommendation
    ) -> Tuple[List[str], List[Dict]]:
        """Scaffold FastAPI project structure."""
        
        directories = [
            "app/routes",
            "app/services",
            "app/models",
            "app/utils",
            "tests",
            "docs",
            "prompts"
        ]
        
        files = [
            {
                "path": "requirements.txt",
                "content": "fastapi==0.109.0\nuvicorn[standard]==0.27.0\npydantic==2.5.3\npython-dotenv==1.0.0"
            },
            {
                "path": "app/__init__.py",
                "content": ""
            },
            {
                "path": "app/main.py",
                "content": self._generate_fastapi_main(analysis)
            },
            {
                "path": ".env.example",
                "content": "DATABASE_URL=\nSECRET_KEY="
            },
            {
                "path": ".gitignore",
                "content": self._generate_gitignore()
            }
        ]
        
        return directories, files
    
    def _scaffold_cli(
        self,
        analysis: IdeaAnalysis,
        tech_stack: TechStackRecommendation
    ) -> Tuple[List[str], List[Dict]]:
        """Scaffold CLI tool structure."""
        
        name = self._sanitize_name(analysis.title)
        
        directories = [
            f"{name}",
            "tests",
            "docs"
        ]
        
        files = [
            {
                "path": "pyproject.toml",
                "content": self._generate_pyproject(analysis)
            },
            {
                "path": f"{name}/__init__.py",
                "content": ""
            },
            {
                "path": f"{name}/main.py",
                "content": self._generate_cli_main(analysis)
            },
            {
                "path": ".gitignore",
                "content": self._generate_gitignore()
            }
        ]
        
        return directories, files
    
    def _scaffold_generic(
        self,
        analysis: IdeaAnalysis,
        tech_stack: TechStackRecommendation
    ) -> Tuple[List[str], List[Dict]]:
        """Scaffold generic project structure."""
        
        directories = ["src", "tests", "docs", "prompts"]
        files = [
            {"path": ".gitignore", "content": self._generate_gitignore()},
            {"path": "README.md", "content": f"# {analysis.title}\n\n{analysis.description}"}
        ]
        
        return directories, files

    def _scaffold_fullstack(
        self,
        analysis: IdeaAnalysis,
        tech_stack: TechStackRecommendation
    ) -> Tuple[List[str], List[Dict]]:
        """Scaffold full-stack project with separate backend and frontend folders."""

        directories = [
            "backend",
            "backend/app",
            "backend/app/routes",
            "backend/app/services",
            "backend/app/models",
            "backend/app/utils",
            "backend/tests",
            "frontend",
            "frontend/src",
            "frontend/src/app",
            "frontend/src/components",
            "frontend/src/lib",
            "frontend/src/hooks",
            "frontend/public",
            "docs",
            "prompts"
        ]

        files = []

        # Backend files (FastAPI structure)
        backend_files = [
            {
                "path": "backend/requirements.txt",
                "content": "fastapi==0.109.0\nuvicorn[standard]==0.27.0\npydantic==2.5.3\npython-dotenv==1.0.0\nsqlalchemy==2.0.23\nalembic==1.13.1"
            },
            {
                "path": "backend/main.py",
                "content": """from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import api_router

app = FastAPI(title=f"{analysis.title} API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")

@app.get("/")
async def root():
    return {"message": "API is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
"""
            },
            {
                "path": "backend/app/__init__.py",
                "content": ""
            },
            {
                "path": "backend/app/routes/__init__.py",
                "content": """from fastapi import APIRouter
from .items import router as items_router

api_router = APIRouter()
api_router.include_router(items_router, prefix="/items", tags=["items"])
"""
            },
            {
                "path": "backend/app/routes/items.py",
                "content": """from fastapi import APIRouter, HTTPException
from typing import List
from ..models.item import Item, ItemCreate, ItemUpdate

router = APIRouter()

# In-memory storage for demo (replace with database)
items_db = []
item_id_counter = 1

@router.get("/", response_model=List[Item])
async def get_items():
    return items_db

@router.post("/", response_model=Item)
async def create_item(item: ItemCreate):
    global item_id_counter
    new_item = Item(id=item_id_counter, **item.model_dump())
    items_db.append(new_item)
    item_id_counter += 1
    return new_item

@router.get("/{item_id}", response_model=Item)
async def get_item(item_id: int):
    for item in items_db:
        if item.id == item_id:
            return item
    raise HTTPException(status_code=404, detail="Item not found")

@router.put("/{item_id}", response_model=Item)
async def update_item(item_id: int, item_update: ItemUpdate):
    for i, item in enumerate(items_db):
        if item.id == item_id:
            updated_item = Item(id=item_id, **item_update.model_dump())
            items_db[i] = updated_item
            return updated_item
    raise HTTPException(status_code=404, detail="Item not found")

@router.delete("/{item_id}")
async def delete_item(item_id: int):
    for i, item in enumerate(items_db):
        if item.id == item_id:
            del items_db[i]
            return {"message": "Item deleted"}
    raise HTTPException(status_code=404, detail="Item not found")
"""
            },
            {
                "path": "backend/app/models/__init__.py",
                "content": """from .item import Item, ItemCreate, ItemUpdate

__all__ = ["Item", "ItemCreate", "ItemUpdate"]
"""
            },
            {
                "path": "backend/app/models/item.py",
                "content": """from pydantic import BaseModel
from typing import Optional

class ItemBase(BaseModel):
    title: str
    description: Optional[str] = None

class ItemCreate(ItemBase):
    pass

class ItemUpdate(ItemBase):
    title: Optional[str] = None

class Item(ItemBase):
    id: int

    class Config:
        from_attributes = True
"""
            }
        ]

        # Frontend files (Next.js structure)
        frontend_files = [
            {
                "path": "frontend/package.json",
                "content": f'''{{
  "name": "{analysis.title.lower().replace(" ", "-")}-frontend",
  "version": "0.1.0",
  "private": true,
  "scripts": {{
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint"
  }},
  "dependencies": {{
    "next": "14.0.4",
    "react": "^18",
    "react-dom": "^18",
    "@types/node": "^20",
    "@types/react": "^18",
    "@types/react-dom": "^18",
    "typescript": "^5",
    "tailwindcss": "^3.3.0",
    "autoprefixer": "^10.0.1",
    "postcss": "^8",
    "eslint": "^8",
    "eslint-config-next": "14.0.4"
  }}
}}'''
            },
            {
                "path": "frontend/next.config.js",
                "content": """/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8000/api/:path*',
      },
    ]
  },
}

module.exports = nextConfig
"""
            },
            {
                "path": "frontend/tailwind.config.ts",
                "content": """import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
export default config
"""
            },
            {
                "path": "frontend/postcss.config.mjs",
                "content": """/** @type {import('postcss-load-config').Config} */
const config = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}

export default config
"""
            },
            {
                "path": "frontend/src/app/layout.tsx",
                "content": """import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: '""" + analysis.title + """',
  description: '""" + analysis.description + """',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={inter.className}>{children}</body>
    </html>
  )
}
"""
            },
            {
                "path": "frontend/src/app/page.tsx",
                "content": """'use client'

import { useState, useEffect } from 'react'

interface Item {
  id: number
  title: string
  description?: string
}

export default function Home() {
  const [items, setItems] = useState<Item[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchItems()
  }, [])

  const fetchItems = async () => {
    try {
      const response = await fetch('/api/items')
      const data = await response.json()
      setItems(data)
    } catch (error) {
      console.error('Failed to fetch items:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return <div className="flex items-center justify-center min-h-screen">Loading...</div>
  }

  return (
    <main className="container mx-auto px-4 py-8">
      <h1 className="text-4xl font-bold mb-8">""" + analysis.title + """</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {items.map((item) => (
          <div key={item.id} className="border rounded-lg p-4 shadow-sm">
            <h2 className="text-xl font-semibold">{item.title}</h2>
            {item.description && (
              <p className="text-gray-600 mt-2">{item.description}</p>
            )}
          </div>
        ))}
      </div>
    </main>
  )
}
"""
            },
            {
                "path": "frontend/src/app/globals.css",
                "content": """@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  --foreground-rgb: 0, 0, 0;
  --background-start-rgb: 214, 219, 220;
  --background-end-rgb: 255, 255, 255;
}

@media (prefers-color-scheme: dark) {
  :root {
    --foreground-rgb: 255, 255, 255;
    --background-start-rgb: 0, 0, 0;
    --background-end-rgb: 0, 0, 0;
  }
}

body {
  color: rgb(var(--foreground-rgb));
  background: linear-gradient(
      to bottom,
      transparent,
      rgb(var(--background-end-rgb))
    )
    rgb(var(--background-start-rgb));
}
"""
            },
            {
                "path": "frontend/tsconfig.json",
                "content": """{
  "compilerOptions": {
    "target": "es5",
    "lib": ["dom", "dom.iterable", "es6"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [
      {
        "name": "next"
      }
    ],
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"]
    }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
"""
            }
        ]

        # Docker Compose for fullstack
        docker_files = [
            {
                "path": "docker-compose.yml",
                "content": """version: '3.8'

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=sqlite:///./app.db
    volumes:
      - ./backend:/app
    command: uvicorn main:app --host 0.0.0.0 --port 8000 --reload

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    volumes:
      - ./frontend:/app
      - /app/node_modules
    command: npm run dev
    depends_on:
      - backend
"""
            },
            {
                "path": "backend/Dockerfile",
                "content": """FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
"""
            },
            {
                "path": "frontend/Dockerfile",
                "content": """FROM node:18-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

EXPOSE 3000

CMD ["npm", "run", "dev"]
"""
            }
        ]

        files.extend(backend_files)
        files.extend(frontend_files)
        files.extend(docker_files)

        return directories, files

    def _generate_package_json(self, analysis: IdeaAnalysis) -> str:
        """Generate package.json."""
        name = self._sanitize_name(analysis.title)
        return json.dumps({
            "name": name,
            "version": "0.1.0",
            "private": True,
            "scripts": {
                "dev": "next dev",
                "build": "next build",
                "start": "next start",
                "lint": "next lint"
            },
            "dependencies": {
                "next": "14.x",
                "react": "18.x",
                "react-dom": "18.x"
            },
            "devDependencies": {
                "typescript": "^5.x",
                "@types/node": "^20.x",
                "@types/react": "^18.x",
                "tailwindcss": "^3.x"
            }
        }, indent=2)
    
    def _generate_tsconfig(self) -> str:
        """Generate tsconfig.json."""
        return json.dumps({
            "compilerOptions": {
                "target": "ES2017",
                "lib": ["dom", "dom.iterable", "esnext"],
                "strict": True,
                "module": "esnext",
                "moduleResolution": "bundler",
                "paths": {"@/*": ["./src/*"]}
            },
            "include": ["src"],
            "exclude": ["node_modules"]
        }, indent=2)
    
    def _generate_env_example(self, tech_stack: TechStackRecommendation) -> str:
        """Generate .env.example."""
        lines = ["# Environment Configuration", ""]
        
        if "supabase" in str(tech_stack.backend).lower():
            lines.extend([
                "NEXT_PUBLIC_SUPABASE_URL=",
                "NEXT_PUBLIC_SUPABASE_ANON_KEY=",
                "SUPABASE_SERVICE_ROLE_KEY="
            ])
        
        lines.extend([
            "",
            "# API Keys",
            "OPENAI_API_KEY="
        ])
        
        return "\n".join(lines)
    
    def _generate_gitignore(self) -> str:
        """Generate .gitignore."""
        return """# Dependencies
node_modules/
venv/
__pycache__/

# Environment
.env
.env.local

# Build
.next/
dist/
build/

# IDE
.vscode/
.idea/

# OS
.DS_Store
Thumbs.db

# Logs
*.log
"""
    
    def _generate_layout(self, analysis: IdeaAnalysis) -> str:
        """Generate Next.js layout.tsx."""
        desc_short = analysis.description[:100] if len(analysis.description) > 100 else analysis.description
        return f'''import type {{ Metadata }} from "next";
import "./globals.css";

export const metadata: Metadata = {{
  title: "{analysis.title}",
  description: "{desc_short}",
}};

export default function RootLayout({{
  children,
}}: {{
  children: React.ReactNode;
}}) {{
  return (
    <html lang="en">
      <body>{{children}}</body>
    </html>
  );
}}
'''
    
    def _generate_homepage(self, analysis: IdeaAnalysis) -> str:
        """Generate Next.js page.tsx."""
        return f'''export default function Home() {{
  return (
    <main className="min-h-screen p-8">
      <h1 className="text-4xl font-bold">{analysis.title}</h1>
      <p className="mt-4 text-gray-600">{analysis.description}</p>
    </main>
  );
}}
'''
    
    def _generate_fastapi_main(self, analysis: IdeaAnalysis) -> str:
        """Generate FastAPI main.py."""
        return f'''"""
{analysis.title} API
"""
from fastapi import FastAPI

app = FastAPI(
    title="{analysis.title}",
    description="{analysis.description}",
    version="0.1.0"
)

@app.get("/")
async def root():
    return {{"message": "Welcome to {analysis.title}"}}

@app.get("/health")
async def health():
    return {{"status": "healthy"}}
'''
    
    def _generate_pyproject(self, analysis: IdeaAnalysis) -> str:
        """Generate pyproject.toml for CLI."""
        name = self._sanitize_name(analysis.title)
        return f'''[tool.poetry]
name = "{name}"
version = "0.1.0"
description = "{analysis.description}"

[tool.poetry.dependencies]
python = "^3.10"
typer = "^0.9.0"
rich = "^13.0.0"

[tool.poetry.scripts]
{name} = "{name}.main:app"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
'''
    
    def _generate_cli_main(self, analysis: IdeaAnalysis) -> str:
        """Generate CLI main.py."""
        return f'''"""
{analysis.title} CLI
"""
import typer
from rich import print

app = typer.Typer(help="{analysis.description}")

@app.command()
def hello(name: str = "World"):
    """Say hello."""
    print(f"[bold green]Hello {{name}}![/bold green]")

if __name__ == "__main__":
    app()
'''
    
    def _generate_cursorrules(
        self,
        analysis: IdeaAnalysis,
        tech_stack: TechStackRecommendation
    ) -> str:
        """Generate .cursorrules file."""
        project_type = analysis.project_type
        if isinstance(project_type, str):
            type_value = project_type
        else:
            type_value = project_type.value
        
        return f"""# Project: {analysis.title}
# Type: {type_value}

## Tech Stack
{self._format_tech_stack(tech_stack)}

## Code Style
- Use TypeScript strict mode
- Prefer functional components
- Use meaningful variable names
- Add comments for complex logic

## Project Context
{analysis.description}

## MVP Features
{chr(10).join('- ' + f for f in analysis.mvp_features)}

## Documentation
- Read docs/00_MASTER_PLAN.md for project overview
- Read docs/01_PHASE_1_MVP.md for current phase

## Priority
Start with prompts/01_setup.md
"""
    
    def _format_tech_stack(self, tech_stack: TechStackRecommendation) -> str:
        """Format tech stack for cursorrules."""
        lines = []
        
        if tech_stack.frontend:
            lines.append("### Frontend")
            for k, v in tech_stack.frontend.items():
                lines.append(f"- {k}: {v}")
        
        if tech_stack.backend:
            lines.append("### Backend")
            for k, v in tech_stack.backend.items():
                lines.append(f"- {k}: {v}")
        
        return "\n".join(lines)
    
    def _generate_documentation(
        self,
        analysis: IdeaAnalysis,
        tech_stack: TechStackRecommendation,
        architecture: ProjectArchitecture
    ) -> Dict[str, str]:
        """Generate all documentation files."""
        
        return {
            "00_MASTER_PLAN.md": self._generate_master_plan(analysis, tech_stack),
            "01_PHASE_1_MVP.md": self._generate_phase_spec(analysis, tech_stack, architecture),
            "03_ARCHITECTURE.md": self._generate_arch_doc(architecture),
            "04_DATA_MODELS.md": self._generate_data_models_doc(architecture)
        }
    
    def _generate_master_plan(
        self,
        analysis: IdeaAnalysis,
        tech_stack: TechStackRecommendation
    ) -> str:
        """Generate master plan document."""
        project_size = analysis.project_size
        if isinstance(project_size, str):
            size_value = project_size
        else:
            size_value = project_size.value
        
        return f"""# {analysis.title} — Master Plan

## Vision
{analysis.description}

## Problem Statement
{analysis.problem_statement}

## Target User
{analysis.target_user}

## Value Proposition
{analysis.value_proposition}

---

## Technical Overview

### Tech Stack
{self._format_tech_stack(tech_stack)}

### Estimated Scope
- **Size:** {size_value}
- **Estimated Hours:** {analysis.estimated_hours}

---

## Feature Roadmap

### MVP Features
{chr(10).join('- [ ] ' + f for f in analysis.mvp_features)}

### Future Features
{chr(10).join('- [ ] ' + f for f in analysis.future_features)}

---

## Risks & Assumptions

### Risks
{chr(10).join('- ' + r for r in analysis.risks)}

### Assumptions
{chr(10).join('- ' + a for a in analysis.assumptions)}
"""
    
    def _generate_phase_spec(
        self,
        analysis: IdeaAnalysis,
        tech_stack: TechStackRecommendation,
        architecture: ProjectArchitecture
    ) -> str:
        """Generate Phase 1 specification."""
        endpoints_str = chr(10).join(
            f"- `{e.get('method', 'GET')} {e.get('path', '')}` — {e.get('description', '')}" 
            for e in architecture.api_endpoints[:10]
        )
        
        models_str = chr(10).join(
            f"### {m.get('name', 'Model')}" + chr(10) + f"Fields: {m.get('fields', '')}" 
            for m in architecture.data_models[:5]
        )
        
        return f"""# Phase 1: MVP Specification

## Overview
Build the core functionality for {analysis.title}.

## Goal
{analysis.value_proposition}

## Features for This Phase
{chr(10).join('- [ ] ' + f for f in analysis.mvp_features)}

---

## API Endpoints

{endpoints_str}

---

## Data Models

{models_str}

---

## Success Criteria
- Core features working
- Basic UI functional
- Can demo end-to-end flow
"""
    
    def _generate_arch_doc(self, architecture: ProjectArchitecture) -> str:
        """Generate architecture document."""
        components_str = chr(10).join(
            f"### {c.get('name', 'Component')}" + chr(10) + 
            f"{c.get('purpose', '')}" + chr(10) + 
            f"Technology: {c.get('technology', '')}" 
            for c in architecture.components
        )
        
        return f"""# System Architecture

## Overview
{architecture.overview}

## System Diagram
```
{architecture.diagrams.get('system_diagram', '')}
```

## Components
{components_str}

## Data Flow
{architecture.data_flow}
"""
    
    def _generate_data_models_doc(self, architecture: ProjectArchitecture) -> str:
        """Generate data models document."""
        lines = ["# Data Models", ""]
        
        for model in architecture.data_models:
            lines.extend([
                f"## {model.get('name', 'Model')}",
                f"**Fields:** {model.get('fields', '')}",
                f"**Relationships:** {model.get('relationships', 'None')}",
                ""
            ])
        
        return "\n".join(lines)
    
    def _generate_cursor_prompts(
        self,
        analysis: IdeaAnalysis,
        tech_stack: TechStackRecommendation
    ) -> List[Dict]:
        """Generate Cursor AI prompts."""
        
        project_type = analysis.project_type
        if isinstance(project_type, str):
            type_value = project_type
        else:
            type_value = project_type.value
        
        prompts = [
            {
                "filename": "CURSOR_COMMANDS.md",
                "content": f"""# Cursor Commands for {analysis.title}

## Getting Started

**Prompt 01: Project Setup**
```
@Cursor, set up this project:

1. Read .cursorrules for context
2. Install dependencies
3. Set up the basic structure
4. Create initial configuration

Reference docs/00_MASTER_PLAN.md for overview.
```

---

## Phase 1 Implementation

**Prompt 02: Core Feature**
```
@Cursor, implement the first core feature:

1. Read docs/01_PHASE_1_MVP.md
2. Implement the data model
3. Create the API endpoint
4. Build the UI component
```

---

## Testing

**Prompt: Add Tests**
```
@Cursor, add tests for the implemented features:

1. Unit tests for core logic
2. Integration tests for API
3. Component tests for UI
```
"""
            },
            {
                "filename": "01_setup.md",
                "content": f"""# Setup Prompt

@Cursor, help me set up {analysis.title}:

1. This is a {type_value} project
2. Check .cursorrules for tech stack
3. Install all dependencies
4. Set up the project structure
5. Create placeholder files

The MVP features are:
{chr(10).join('- ' + f for f in analysis.mvp_features)}

Start with the basic setup.
"""
            }
        ]
        
        return prompts
    
    def _generate_readme(
        self,
        analysis: IdeaAnalysis,
        tech_stack: TechStackRecommendation,
        architecture: ProjectArchitecture
    ) -> str:
        """Generate README.md."""
        return f"""# {analysis.title}

{analysis.description}

## Quick Start

```bash
# Install dependencies
npm install  # or pip install -r requirements.txt

# Set up environment
cp .env.example .env

# Run development server
npm run dev  # or python -m app.main
```

## Documentation

- [Master Plan](docs/00_MASTER_PLAN.md) — Project overview
- [Phase 1 MVP](docs/01_PHASE_1_MVP.md) — Current phase spec
- [Architecture](docs/03_ARCHITECTURE.md) — System design

## Development with Cursor

1. Open project in Cursor
2. Read `.cursorrules` for context
3. Start with `prompts/01_setup.md`
4. Follow prompts in `prompts/CURSOR_COMMANDS.md`

## Tech Stack

{self._format_tech_stack(tech_stack)}

---

*Generated by ArmLenQuant Ideas Machine*
"""

