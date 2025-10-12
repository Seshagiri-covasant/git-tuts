/**
 * CSV Export Utilities
 * Functions for exporting table data to CSV format
 */

export const exportToCSV = (data: any[], filename: string = 'table_data.csv') => {
  if (!data || data.length === 0) {
    console.error('No data to export');
    return;
  }

  try {
    // Get all unique keys from the data
    const allKeys = Array.from(
      new Set(data.flatMap((item: any) => Object.keys(item)))
    );

    // Create CSV header
    const csvHeader = allKeys.join(',');

    // Create CSV rows
    const csvRows = data.map((row: any) => {
      return allKeys.map((key: string) => {
        const value = row[key] ?? '';
        // Handle special characters and commas in values
        const stringValue = String(value);
        // If the value contains comma, newline, or quote, wrap it in quotes
        if (stringValue.includes(',') || stringValue.includes('\n') || stringValue.includes('"')) {
          return `"${stringValue.replace(/"/g, '""')}"`;
        }
        return stringValue;
      }).join(',');
    });

    // Combine header and rows
    const csvContent = [csvHeader, ...csvRows].join('\n');

    // Create and download the file
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    
    if (link.download !== undefined) {
      // Create a temporary URL for the blob
      const url = URL.createObjectURL(blob);
      link.setAttribute('href', url);
      link.setAttribute('download', filename);
      link.style.visibility = 'hidden';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      
      // Clean up the URL object
      URL.revokeObjectURL(url);
    } else {
      // Fallback for browsers that don't support the download attribute
      const url = URL.createObjectURL(blob);
      window.open(url);
      URL.revokeObjectURL(url);
    }
  } catch (error) {
    console.error('Error exporting CSV:', error);
  }
};

export const generateCSVFilename = (prefix: string = 'table_data') => {
  const now = new Date();
  const timestamp = now.toISOString().replace(/[:.]/g, '-').slice(0, 19);
  return `${prefix}_${timestamp}.csv`;
}; 