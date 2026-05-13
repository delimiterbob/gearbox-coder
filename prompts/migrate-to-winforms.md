# Target: C# WinForms .NET 10

Migrate the provided source code to a **C# Windows Forms application targeting .NET 10**.

## Target Stack Requirements

- **SDK:** `Microsoft.NET.Sdk`
- **TargetFramework:** `net10.0-windows`
- **UseWindowsForms:** `true`
- **Output type:** `WinExe`
- **Nullable:** `enable`
- **ImplicitUsings:** `enable`

## Control Mapping Guidelines

| Legacy Control | WinForms .NET 10 Equivalent |
|---|---|
| TextBox / Edit / Entry | `TextBox` |
| Label / Static Text | `Label` |
| Button / CommandButton | `Button` |
| ListBox | `ListBox` |
| ComboBox / DropDown | `ComboBox` |
| DataGrid / Grid / Browse | `DataGridView` |
| CheckBox | `CheckBox` |
| RadioButton / OptionButton | `RadioButton` |
| Timer | `System.Windows.Forms.Timer` |
| Menu | `MenuStrip` + `ToolStripMenuItem` |
| Modal Dialog | Separate `Form` shown with `ShowDialog()` |
| Tab Control | `TabControl` + `TabPage` |
| TreeView | `TreeView` |

## Data Access

- Replace legacy data access (ADO, ADODB, DAO, JDBC, SQLCA, xBase) with **ADO.NET** or **Entity Framework Core**
- For in-memory data: use `DataTable`, `DataSet`, `BindingSource`, `BindingList<T>`
- For database: use `Microsoft.Data.SqlClient` or `Microsoft.Data.Sqlite`

## Project File Template

```xml
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <OutputType>WinExe</OutputType>
    <TargetFramework>net10.0-windows</TargetFramework>
    <Nullable>enable</Nullable>
    <UseWindowsForms>true</UseWindowsForms>
    <ImplicitUsings>enable</ImplicitUsings>
  </PropertyGroup>
</Project>
```
