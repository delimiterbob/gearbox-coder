# Target: C# Blazor Server .NET 10

Migrate the provided source code to a **C# Blazor Server application targeting .NET 10**.

## Target Stack Requirements

- **SDK:** `Microsoft.NET.Sdk.Web`
- **TargetFramework:** `net10.0`
- **Nullable:** `enable`
- **ImplicitUsings:** `enable`
- **Render mode:** Interactive Server (`@rendermode InteractiveServer`)

## Architecture

- Each legacy form/window/page becomes a **Razor component** (`.razor` file)
- Business logic goes in **service classes** injected via DI
- State management via component parameters, cascading values, or injected services
- Navigation via `NavigationManager` and `@page` directives

## Control Mapping Guidelines

| Legacy Control | Blazor Equivalent |
|---|---|
| TextBox / Edit / Entry | `<InputText>` or `<input @bind="...">` |
| Label / Static Text | `<span>`, `<label>`, or inline `@variable` |
| Button / CommandButton | `<button @onclick="...">` |
| ListBox | `<InputSelect>` or `<select @bind="...">` |
| ComboBox / DropDown | `<InputSelect>` with `@foreach` options |
| DataGrid / Grid / Browse | `<table>` with `@foreach`, or `<QuickGrid>` |
| CheckBox | `<InputCheckbox>` |
| RadioButton | `<InputRadioGroup>` + `<InputRadio>` |
| Timer | `System.Timers.Timer` + `InvokeAsync(StateHasChanged)` |
| Modal Dialog | Component with conditional rendering or a dialog library |
| Tab Control | Manual tab component with `@if` / CSS classes |
| Menu | `<NavMenu>` component |
| Master-Detail | Parent component with `EventCallback` to child component |

## Data Access

- Replace legacy data access with **Entity Framework Core** (preferred) or **ADO.NET**
- Register DbContext / repositories in `Program.cs` via DI
- For in-memory data: use `List<T>` in an injected service class

## Form/Validation

- Use `<EditForm>` with `Model` binding
- Data annotations for validation (`[Required]`, `[Range]`, etc.)
- `<DataAnnotationsValidator>` + `<ValidationSummary>`

## Project File Template

```xml
<Project Sdk="Microsoft.NET.Sdk.Web">
  <PropertyGroup>
    <TargetFramework>net10.0</TargetFramework>
    <Nullable>enable</Nullable>
    <ImplicitUsings>enable</ImplicitUsings>
  </PropertyGroup>
</Project>
```

## File Structure

```
ProjectName/
  Program.cs
  Components/
    App.razor
    Routes.razor
    Layout/
      MainLayout.razor
      NavMenu.razor
    Pages/
      Home.razor
      [MigratedPage].razor
  Models/
    [BusinessObjects].cs
  Services/
    [DataService].cs
  wwwroot/
    css/
```
