"use client";

interface Column<T> {
  key: keyof T | string;
  header: string;
  render?: (row: T) => React.ReactNode;
}

interface TableProps<T extends object> {
  columns: Column<T>[];
  data: T[];
  keyField: keyof T;
  className?: string;
}

export function Table<T extends object>({
  columns,
  data,
  keyField,
  className = "",
}: TableProps<T>) {
  return (
    <div className={`overflow-x-auto rounded-lg border border-gray-200 ${className}`}>
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            {columns.map((col) => (
              <th
                key={String(col.key)}
                className="px-4 py-3 text-left text-sm font-semibold text-gray-900"
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {data.map((row, index) => (
            <tr
              key={String((row as Record<string, unknown>)[keyField as string] ?? index)}
              className="hover:bg-gray-50/50 transition-colors"
            >
              {columns.map((col) => (
                <td key={String(col.key)} className="px-4 py-3 text-sm text-gray-700">
                  {col.render
                    ? col.render(row)
                    : String((row as Record<string, unknown>)[col.key as string] ?? "")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
