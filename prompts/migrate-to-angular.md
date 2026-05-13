# Target: C# .NET 10 + Angular

Migrate the provided source code to a **C# .NET 10 Web API backend + Angular frontend**.

## Target Stack Requirements

### Backend (C# .NET 10 Web API)
- **SDK:** `Microsoft.NET.Sdk.Web`
- **TargetFramework:** `net10.0`
- **Nullable:** `enable`
- **ImplicitUsings:** `enable`
- Minimal API or Controller-based (prefer Controllers for CRUD operations)
- JSON serialization via `System.Text.Json`

### Frontend (Angular 19+)
- **TypeScript** strict mode
- **Standalone components** (no NgModule)
- **Angular Signals** for reactive state where appropriate
- **HttpClient** for API calls
- **Angular Material** or plain HTML for UI controls

## Architecture

- Legacy forms become **Angular components** (`.ts` + `.html` + `.css`)
- Business logic lives in the **.NET API** (Controllers + Services)
- Angular services call the API via `HttpClient`
- DTOs shared conceptually between API responses and Angular interfaces

## Control Mapping Guidelines

| Legacy Control | Angular Equivalent |
|---|---|
| TextBox / Edit / Entry | `<input [(ngModel)]="...">` or reactive `FormControl` |
| Label / Static Text | `<span>{{ value }}</span>` or `<label>` |
| Button / CommandButton | `<button (click)="...">` |
| ListBox | `<select>` with `*ngFor` |
| ComboBox / DropDown | `<select [(ngModel)]="...">` with `<option *ngFor>` |
| DataGrid / Grid / Browse | `<table>` with `*ngFor`, or `<mat-table>` |
| CheckBox | `<input type="checkbox" [(ngModel)]="...">` |
| Modal Dialog | Angular Material `MatDialog` or custom overlay component |
| Tab Control | `<mat-tab-group>` or custom tabs |
| Master-Detail | Parent/child components with `@Input()` / `@Output()` |

## Data Access (Backend)

- Replace legacy data access with **Entity Framework Core** or **ADO.NET**
- Expose via REST endpoints: `GET /api/resource`, `POST`, `PUT`, `DELETE`
- For in-memory data: use a singleton service with `List<T>`

## API File Structure

```
output/
  Api/
    Program.cs
    Controllers/
      [Resource]Controller.cs
    Models/
      [BusinessObject].cs
    Services/
      [DataService].cs
    Api.csproj
  ClientApp/
    src/
      app/
        components/
          [feature]/
            [feature].component.ts
            [feature].component.html
            [feature].component.css
        models/
          [model].ts
        services/
          [data].service.ts
        app.component.ts
        app.routes.ts
      index.html
      main.ts
    angular.json
    package.json
    tsconfig.json
```

## Backend Project File Template

```xml
<Project Sdk="Microsoft.NET.Sdk.Web">
  <PropertyGroup>
    <TargetFramework>net10.0</TargetFramework>
    <Nullable>enable</Nullable>
    <ImplicitUsings>enable</ImplicitUsings>
  </PropertyGroup>
</Project>
```
