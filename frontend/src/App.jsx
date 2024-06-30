import React, { useState } from "react";
import DeviceForm from "./components/DeviceForm";
import ModeForm from "./components/ModeForm";

const App = () => {
  const [deviceInfo, setDeviceInfo] = useState(null);
  const [mode, setMode] = useState("");
  const [dev, setDev] = useState("");
  const [mac, setMac] = useState("");
  const [setting, setSetting] = useState(0x12345678);

  const handleConnect = (info) => {
    setDeviceInfo(info);
  };

  const handleExecute = (result) => {
    console.log(result);
  };

  const handleModeSelect = (selectedMode) => {
    setMode(selectedMode);
  };

  return (
    <div className="container mx-auto p-4">
      <h1 className="text-2xl font-bold mb-4">Device Dashboard</h1>
      <DeviceForm
        onConnect={handleConnect}
        mac={mac}
        dev={dev}
        setting={setting}
        setDev={setDev}
        setMac={setMac}
        setSetting={setSetting}
      />
      {deviceInfo && (
        <div className="mt-4">
          <h2 className="text-xl font-bold">Device Info</h2>
          <pre className="bg-gray-100 p-4 rounded">
            {JSON.stringify(deviceInfo, null, 2)}
          </pre>
        </div>
      )}
      {deviceInfo && (
        <div className="mt-4">
          <h2 className="text-xl font-bold">Select Mode</h2>
          <div className="flex space-x-4 mt-2">
            <button
              onClick={() => handleModeSelect("mode1")}
              className={`bg-blue-500 text-white py-2 px-4 rounded ${
                mode === "mode1" ? "bg-blue-700" : ""
              }`}
            >
              Mode 1
            </button>
            <button
              onClick={() => handleModeSelect("mode2")}
              className={`bg-blue-500 text-white py-2 px-4 rounded ${
                mode === "mode2" ? "bg-blue-700" : ""
              }`}
            >
              Mode 2
            </button>
          </div>
        </div>
      )}
      {mode && (
        <ModeForm
          mode={mode}
          onExecute={handleExecute}
          dev={dev}
          mac={mac}
          setMac={setMac}
          setting={setting}
          setSetting={setSetting}
        />
      )}
    </div>
  );
};

export default App;
