import React, {
  createContext,
  useState,
  useContext,
  useEffect,
  ReactNode,
} from 'react';

// Toast type definition
type ToastType = 'success' | 'error' | 'deleted';

interface ToastData {
  message: string;
  type: ToastType;
  data?: string;
}

interface ToasterContextType {
  showToast: (message: string, type: ToastType, data?: string) => void;
}

// Create context
const ToasterContext = createContext<ToasterContextType | undefined>(undefined);

// Provider props
interface ToasterProviderProps {
  children: ReactNode;
}

// Provider
export const ToasterProvider: React.FC<ToasterProviderProps> = ({ children }) => {
  const [toast, setToast] = useState<ToastData | null>(null);

  const showToast = (message: string, type: ToastType, data?: string) => {
    setToast({ message, type, data });
  };

  const hideToast = () => {
    setToast(null);
  };

  // Auto-dismiss after 5 seconds
  useEffect(() => {
    if (toast) {
      const timer = setTimeout(() => {
        hideToast();
      }, 5000);
      return () => clearTimeout(timer);
    }
  }, [toast]);

  return (
    <ToasterContext.Provider value={{ showToast }}>
      {children}

      {/* Toast Component */}
      {toast && (
        <div
          className={`position-fixed top-0 end-0 m-4 p-3 rounded shadow ${getBootstrapBgColor(
            toast.type
          )} text-dark`}
          style={{
            zIndex: 1050,
            marginTop: '40px',
            maxWidth: '300px',
            width: '100%',
          }}
        >
          <div className="d-flex justify-content-between align-items-start">
            <div className="d-flex">
              {/* Optional: Add icon if needed */}
              {/* <img
                src={getImageSrc(toast.type)}
                alt={toast.type}
                style={{ width: '24px', height: '24px', marginRight: '8px' }}
              /> */}
              <div>
                <div className="fw-semibold text-white text-[0.875rem]">{toast.message}</div>
                {/* {toast.data && (
                  <div className="text-muted small">{toast.data}</div>
                )} */}
              </div>
            </div>
            <button
              onClick={hideToast}
             className="btn-close btn-close-white ms-2 size-2"
              aria-label="Close"
            ></button>
          </div>
        </div>
      )}
    </ToasterContext.Provider>
  );
};

// Helper to get image icon based on toast type (optional)
const getImageSrc = (type: ToastType): string => {
  switch (type) {
    case 'success':
      return '/images/successToaster.svg';
    case 'deleted':
      return '/images/Delete.svg';
    case 'error':
    default:
      return '/images/error.svg';
  }
};

// Helper to map toast type to Bootstrap background class
const getBootstrapBgColor = (type: ToastType): string => {
  switch (type) {
    case 'success':
      return 'purple-bg'; // <-- Custom class directly
    case 'deleted':
    case 'error':
      return 'bg-danger'; // Using Bootstrap class
    default:
      return 'bg-light';
  }
};


// Custom hook
export const useToaster = (): ToasterContextType => {
  const context = useContext(ToasterContext);
  if (context === undefined) {
    throw new Error('useToaster must be used within a ToasterProvider');
  }
  return context;
};
