// components/Loader.tsx
const Loader = () => {
  return (
    <div className="fixed inset-0 z-50 bg-black/50 dark:bg-gray-900/70 backdrop-blur-sm flex items-center justify-center">
      <div className="w-12 h-12 border-4 border-[#6658dd] border-t-transparent rounded-full animate-spin"></div>
    </div>
  );
};

export default Loader;
