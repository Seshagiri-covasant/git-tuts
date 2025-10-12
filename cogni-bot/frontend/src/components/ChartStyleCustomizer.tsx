import React, { useState, useEffect } from 'react';
import { Palette, Settings, RotateCcw, Save, ChevronRight, Download, Sparkles } from 'lucide-react';
import { ColorPicker, useColor } from 'react-color-palette';
import 'react-color-palette/css';

interface ColorTheme {
  name: string;
  colors: string[];
  background: string;
  textColor: string;
  gridColor: string;
  borderColor: string;
}

interface ChartStyleCustomizerProps {
  chartConfig: any;
  onStyleChange: (newConfig: any) => void;
  isOpen: boolean;
  onToggle: (e?: React.MouseEvent) => void;
}

const ChartStyleCustomizer: React.FC<ChartStyleCustomizerProps> = ({
  chartConfig,
  onStyleChange,
  isOpen,
  onToggle,
}) => {
  const [activeColorIndex, setActiveColorIndex] = useState(0);
  const [customColors, setCustomColors] = useState<string[]>([]);
  const [selectedTheme, setSelectedTheme] = useState<string>('covasant');
  const [showColorPicker, setShowColorPicker] = useState(false);
  const [color, setColor] = useColor('#3B82F6');

  // Professional color themes optimized for data visualization
  const colorThemes: ColorTheme[] = [
    {
      name: 'Covasant Blue',
      colors: ['#3B82F6', '#1E40AF', '#60A5FA', '#93C5FD', '#DBEAFE', '#EFF6FF'],
      background: '#FFFFFF',
      textColor: '#1F2937',
      gridColor: '#E5E7EB',
      borderColor: '#D1D5DB'
    },
    {
      name: 'Corporate Professional',
      colors: ['#374151', '#6B7280', '#9CA3AF', '#D1D5DB', '#F3F4F6', '#F9FAFB'],
      background: '#FFFFFF',
      textColor: '#111827',
      gridColor: '#E5E7EB',
      borderColor: '#D1D5DB'
    },
    {
      name: 'Vibrant Energy',
      colors: ['#EF4444', '#F97316', '#EAB308', '#22C55E', '#3B82F6', '#8B5CF6'],
      background: '#FEFEFE',
      textColor: '#1F2937',
      gridColor: '#F3F4F6',
      borderColor: '#E5E7EB'
    },
    {
      name: 'Modern Purple',
      colors: ['#8B5CF6', '#A78BFA', '#C4B5FD', '#DDD6FE', '#EDE9FE', '#F5F3FF'],
      background: '#FEFEFE',
      textColor: '#4C1D95',
      gridColor: '#E5E7EB',
      borderColor: '#D1D5DB'
    },
    {
      name: 'Ocean Depths',
      colors: ['#0891B2', '#06B6D4', '#67E8F9', '#A5F3FC', '#CFFAFE', '#ECFEFF'],
      background: '#F0F9FF',
      textColor: '#0C4A6E',
      gridColor: '#BAE6FD',
      borderColor: '#7DD3FC'
    },
    {
      name: 'Sunset Warmth',
      colors: ['#DC2626', '#EA580C', '#D97706', '#CA8A04', '#65A30D', '#16A34A'],
      background: '#FFFBEB',
      textColor: '#92400E',
      gridColor: '#FED7AA',
      borderColor: '#FDBA74'
    },
    {
      name: 'Elegant Monochrome',
      colors: ['#000000', '#404040', '#737373', '#A3A3A3', '#D4D4D4', '#F5F5F5'],
      background: '#FFFFFF',
      textColor: '#171717',
      gridColor: '#E5E5E5',
      borderColor: '#D4D4D4'
    },
    {
      name: 'Pastel Dreams',
      colors: ['#FB7185', '#FBBF24', '#34D399', '#60A5FA', '#A78BFA', '#F472B6'],
      background: '#FEFEFE',
      textColor: '#374151',
      gridColor: '#F3F4F6',
      borderColor: '#E5E7EB'
    }
  ];

  // Initialize custom colors from chart config
  useEffect(() => {
    if (chartConfig?.data?.datasets?.[0]?.backgroundColor) {
      const colors = Array.isArray(chartConfig.data.datasets[0].backgroundColor)
        ? chartConfig.data.datasets[0].backgroundColor
        : [chartConfig.data.datasets[0].backgroundColor];
      setCustomColors(colors);
    } else {
      // Set default colors if none exist
      setCustomColors(colorThemes[0].colors);
    }
  }, [chartConfig]);

  const applyTheme = (theme: ColorTheme) => {
    if (!chartConfig) return;

    const updatedConfig = JSON.parse(JSON.stringify(chartConfig)); // Deep clone
    
    // Update dataset colors
    if (updatedConfig.data?.datasets) {
      updatedConfig.data.datasets.forEach((dataset: any, datasetIndex: number) => {
        // Apply colors to background
        if (Array.isArray(dataset.backgroundColor)) {
          dataset.backgroundColor = theme.colors.slice(0, dataset.backgroundColor.length);
        } else {
          dataset.backgroundColor = theme.colors;
        }
        
        // Apply border colors
        if (Array.isArray(dataset.borderColor)) {
          dataset.borderColor = theme.colors.slice(0, dataset.borderColor.length);
        } else {
          dataset.borderColor = theme.colors[datasetIndex % theme.colors.length];
        }
        
        dataset.borderWidth = 2;
      });
    }

    // Enhanced chart options
    if (!updatedConfig.options) updatedConfig.options = {};
    if (!updatedConfig.options.plugins) updatedConfig.options.plugins = {};
    if (!updatedConfig.options.scales) updatedConfig.options.scales = {};

    // Apply legend styling
    updatedConfig.options.plugins.legend = {
      ...updatedConfig.options.plugins.legend,
      labels: {
        ...updatedConfig.options.plugins.legend?.labels,
        color: theme.textColor,
        font: {
          size: 12,
          weight: 500,
          family: "'Inter', 'system-ui', sans-serif"
        },
        usePointStyle: true,
        padding: 20,
        boxWidth: 12,
        boxHeight: 12
      }
    };

    // Apply title styling
    if (updatedConfig.options.plugins.title) {
      updatedConfig.options.plugins.title = {
        ...updatedConfig.options.plugins.title,
        color: theme.textColor,
        font: {
          size: 16,
          weight: 600,
          family: "'Inter', 'system-ui', sans-serif"
        }
      };
    }

    // Apply grid and axis styling
    const axisConfig = {
      grid: {
        color: theme.gridColor,
        lineWidth: 1,
        drawBorder: true,
        borderColor: theme.borderColor,
        borderWidth: 1
      },
      ticks: {
        color: theme.textColor,
        font: {
          size: 11,
          family: "'Inter', 'system-ui', sans-serif"
        }
      }
    };

    updatedConfig.options.scales.x = {
      ...updatedConfig.options.scales.x,
      ...axisConfig
    };

    updatedConfig.options.scales.y = {
      ...updatedConfig.options.scales.y,
      ...axisConfig,
      beginAtZero: true
    };

    // Apply background color (for export)
    updatedConfig.options.plugins.backgroundColor = theme.background;

    setSelectedTheme(theme.name);
    setCustomColors(theme.colors);
    onStyleChange(updatedConfig);
  };

  const updateCustomColor = (colorIndex: number, newColor: string) => {
    if (!chartConfig) return;

    const updatedConfig = JSON.parse(JSON.stringify(chartConfig));
    const newColors = [...customColors];
    newColors[colorIndex] = newColor;
    setCustomColors(newColors);

    // Update chart config with new colors
    if (updatedConfig.data?.datasets) {
      updatedConfig.data.datasets.forEach((dataset: any) => {
        if (Array.isArray(dataset.backgroundColor)) {
          dataset.backgroundColor = [...newColors];
        } else {
          dataset.backgroundColor = newColors[0];
        }
        
        if (Array.isArray(dataset.borderColor)) {
          dataset.borderColor = [...newColors];
        } else {
          dataset.borderColor = newColors[colorIndex];
        }
      });
    }

    setSelectedTheme('Custom');
    onStyleChange(updatedConfig);
  };

  const saveCustomTheme = (e: React.MouseEvent) => {
    e.stopPropagation();
    const customTheme: ColorTheme = {
      name: `Custom Theme ${Date.now()}`,
      colors: customColors,
      background: '#FFFFFF',
      textColor: '#1F2937',
      gridColor: '#E5E7EB',
      borderColor: '#D1D5DB'
    };
    
    const savedThemes = JSON.parse(localStorage.getItem('covasant_chart_themes') || '[]');
    savedThemes.push(customTheme);
    localStorage.setItem('covasant_chart_themes', JSON.stringify(savedThemes));
    
    // You could add a toast notification here
  };

  const resetToDefault = (e: React.MouseEvent) => {
    e.stopPropagation();
    const defaultTheme = colorThemes[0];
    applyTheme(defaultTheme);
  };

  const handleColorPickerChange = (newColor: any) => {
    setColor(newColor);
    updateCustomColor(activeColorIndex, newColor.hex);
  };

  const handleColorClick = (e: React.MouseEvent, index: number, color: string) => {
    e.stopPropagation();
    setActiveColorIndex(index);
    setColor({ hex: color } as any);
    setShowColorPicker(true);
  };

  const handleThemeClick = (e: React.MouseEvent, theme: ColorTheme) => {
    e.stopPropagation();
    applyTheme(theme);
  };

  if (!isOpen) {
    return (
      <button
        onClick={(e) => {
          e.stopPropagation();
          onToggle(e);
        }}
        className="fixed right-4 top-1/2 transform -translate-y-1/2 bg-gradient-to-r from-purple-500 to-pink-500 text-white p-3 rounded-l-xl shadow-2xl border-0 z-40 hover:from-purple-600 hover:to-pink-600 transition-all duration-300 group"
        title="Open Chart Style Customizer"
      >
        <div className="flex items-center space-x-2">
          <Palette className="w-5 h-5" />
          <span className="text-xs font-medium opacity-0 group-hover:opacity-100 transition-opacity duration-200">
            Customize
          </span>
        </div>
      </button>
    );
  }

  return (
    <div 
      className="fixed right-0 top-0 h-full w-96 bg-white dark:bg-gray-900 shadow-2xl border-l border-gray-200 dark:border-gray-700 z-50 overflow-y-auto"
      onClick={(e) => e.stopPropagation()}
    >
      {/* Header */}
      <div className="sticky top-0 z-10 bg-gradient-to-r from-purple-50 to-pink-50 dark:from-purple-900/20 dark:to-pink-900/20 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between p-4">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 bg-gradient-to-r from-purple-500 to-pink-500 rounded-lg flex items-center justify-center">
              <Sparkles className="w-4 h-4 text-white" />
            </div>
            <div>
              <h3 className="font-bold text-gray-900 dark:text-gray-100">Chart Styler</h3>
              <p className="text-xs text-gray-600 dark:text-gray-400">Professional visualization themes</p>
            </div>
          </div>
          <button
            onClick={(e) => {
              e.stopPropagation();
              onToggle(e);
            }}
            className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors rounded-lg hover:bg-white/50 dark:hover:bg-gray-800/50"
          >
            <ChevronRight className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="p-4 space-y-6">
        {/* Theme Presets */}
        <div>
          <h4 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-4 flex items-center">
            <Settings className="w-4 h-4 mr-2 text-purple-500" />
            Professional Themes
          </h4>
          <div className="grid grid-cols-1 gap-3">
            {colorThemes.map((theme, index) => (
              <button
                key={theme.name}
                onClick={(e) => handleThemeClick(e, theme)}
                className={`group p-4 rounded-xl border-2 transition-all duration-200 ${
                  selectedTheme === theme.name
                    ? 'border-purple-500 bg-purple-50 dark:bg-purple-900/20 shadow-lg'
                    : 'border-gray-200 dark:border-gray-600 hover:border-purple-300 dark:hover:border-purple-500 hover:shadow-md'
                }`}
              >
                <div className="flex items-center justify-between mb-3">
                  <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                    {theme.name}
                  </span>
                  {selectedTheme === theme.name && (
                    <div className="w-2 h-2 bg-purple-500 rounded-full"></div>
                  )}
                </div>
                <div className="flex space-x-1 mb-2">
                  {theme.colors.slice(0, 6).map((color, colorIndex) => (
                    <div
                      key={colorIndex}
                      className="w-5 h-5 rounded-md border border-white shadow-sm"
                      style={{ backgroundColor: color }}
                    />
                  ))}
                </div>
                <div className="text-xs text-gray-500 dark:text-gray-400 group-hover:text-gray-600 dark:group-hover:text-gray-300">
                  {theme.colors.length} colors • {index === 0 ? 'Recommended' : 'Professional'}
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Custom Colors */}
        <div>
          <h4 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-4">
            Custom Color Palette
          </h4>
          <div className="grid grid-cols-3 gap-3 mb-4">
            {customColors.slice(0, 9).map((color, index) => (
              <button
                key={index}
                onClick={(e) => handleColorClick(e, index, color)}
                className={`relative w-full h-12 rounded-lg border-2 transition-all duration-200 ${
                  activeColorIndex === index && showColorPicker
                    ? 'border-purple-500 shadow-lg scale-105'
                    : 'border-gray-300 dark:border-gray-600 hover:border-purple-400 hover:scale-102'
                }`}
                style={{ backgroundColor: color }}
                title={`Color ${index + 1}: ${color}`}
              >
                <div className="absolute inset-0 rounded-lg bg-black bg-opacity-0 hover:bg-opacity-10 transition-all duration-200"></div>
                <div className="absolute bottom-1 left-1 text-xs font-mono text-white bg-black bg-opacity-50 px-1 rounded">
                  {index + 1}
                </div>
              </button>
            ))}
          </div>

          {/* Color Picker */}
          {showColorPicker && (
            <div className="bg-gray-50 dark:bg-gray-800 rounded-xl p-4 border border-gray-200 dark:border-gray-700">
              <div className="flex items-center justify-between mb-3">
                <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                  Editing Color #{activeColorIndex + 1}
                </span>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setShowColorPicker(false);
                  }}
                  className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                >
                  ×
                </button>
              </div>
              <div onClick={(e) => e.stopPropagation()}>
                <ColorPicker
                  color={color}
                  onChange={handleColorPickerChange}
                  hideInput={['rgb', 'hsv']}
                  height={120}
                />
              </div>
              <div className="mt-3 text-xs text-gray-500 dark:text-gray-400 font-mono text-center">
                {color.hex.toUpperCase()}
              </div>
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="space-y-3">
          <button
            onClick={saveCustomTheme}
            className="w-full flex items-center justify-center space-x-2 px-4 py-3 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-xl hover:from-blue-700 hover:to-purple-700 transition-all duration-200 font-medium shadow-lg hover:shadow-xl"
          >
            <Save className="w-4 h-4" />
            <span>Save Custom Theme</span>
          </button>
          
          <button
            onClick={resetToDefault}
            className="w-full flex items-center justify-center space-x-2 px-4 py-3 bg-gray-500 text-white rounded-xl hover:bg-gray-600 transition-all duration-200 font-medium"
          >
            <RotateCcw className="w-4 h-4" />
            <span>Reset to Covasant Default</span>
          </button>
        </div>

        {/* Pro Tips */}
        <div className="bg-gradient-to-r from-blue-50 to-purple-50 dark:from-blue-900/20 dark:to-purple-900/20 rounded-xl p-4 border border-blue-200 dark:border-blue-700">
          <h5 className="text-sm font-semibold text-blue-800 dark:text-blue-300 mb-2 flex items-center">
            <Sparkles className="w-4 h-4 mr-1" />
            Pro Styling Tips
          </h5>
          <ul className="text-xs text-blue-700 dark:text-blue-400 space-y-1">
            <li>• Use high contrast colors for better accessibility</li>
            <li>• Corporate themes work best for business presentations</li>
            <li>• Save custom themes to maintain brand consistency</li>
            <li>• Vibrant colors grab attention in dashboards</li>
          </ul>
        </div>

        {/* Brand Info */}
        <div className="text-center py-4 border-t border-gray-200 dark:border-gray-700">
          <p className="text-xs text-gray-500 dark:text-gray-400">
            Powered by <span className="font-semibold text-purple-600 dark:text-purple-400">Covasant</span> Design System
          </p>
        </div>
      </div>
    </div>
  );
};

export default ChartStyleCustomizer; 