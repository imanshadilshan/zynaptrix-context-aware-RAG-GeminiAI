import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';

export interface Machine {
  machine_id: string;
  name: string;
  location: string;
  manual_id: string;
}

export interface SensorMeta {
  sensor_id: string;
  sensor_name: string;
  icon_type: string;
  unit: string;
}

interface MachineState {
  machines: Machine[];
  machineConfigs: Record<string, SensorMeta[]>;
  currentMachineId: string;
  loading: boolean;
  error: string | null;
}

const initialState: MachineState = {
  machines: [],
  machineConfigs: {},
  currentMachineId: 'PUMP-001',
  loading: false,
  error: null,
};

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const fetchMachines = createAsyncThunk('machines/fetchMachines', async () => {
    const response = await fetch(`${API_BASE}/api/machines`);
    if (!response.ok) throw new Error('Failed to fetch machines');
    return (await response.json()) as Machine[];
});

export const registerMachine = createAsyncThunk('machines/registerMachine', async (machineData: any) => {
    // Determine if parameter is FormData or a standard object
    let bodyData: any;
    let headers: Record<string, string> = {};
    
    if (machineData instanceof FormData) {
        // Form Data has its own boundary headers added by fetch
        const machineId = machineData.get('machine_id');
        const name = machineData.get('name');
        const location = machineData.get('location');
        const manualId = machineData.get('manual_id');
        bodyData = JSON.stringify({ machine_id: machineId, name, location, manual_id: manualId });
        headers['Content-Type'] = 'application/json';
    } else {
        bodyData = JSON.stringify(machineData);
        headers['Content-Type'] = 'application/json';
    }

    const response = await fetch(`${API_BASE}/api/machines`, {
        method: 'POST',
        headers,
        body: bodyData,
    });
    if (!response.ok) throw new Error('Failed to register machine');
    return (await response.json()) as Machine;
});

export const deleteMachine = createAsyncThunk('machines/deleteMachine', async (machineId: string) => {
    const response = await fetch(`${API_BASE}/api/machines/delete/${machineId}`, {
        method: 'POST',
    });
    if (!response.ok) throw new Error('Failed to decommission machine');
    return machineId;
});

export const fetchMachineConfig = createAsyncThunk('machines/fetchConfig', async (machineId: string) => {
    // Return empty configuration fallback since ML sensor configurations are skipped in the RAG model
    return { machineId, sensorsMeta: [] };
});

const machineSlice = createSlice({
  name: 'machines',
  initialState,
  reducers: {
    setCurrentMachineId(state, action: PayloadAction<string>) {
      state.currentMachineId = action.payload;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchMachines.pending, (state) => {
        state.loading = true;
      })
      .addCase(fetchMachines.fulfilled, (state, action) => {
        state.loading = false;
        state.machines = action.payload;
      })
      .addCase(fetchMachines.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Unknown error';
      })
      .addCase(registerMachine.pending, (state) => {
        state.loading = true;
      })
      .addCase(registerMachine.fulfilled, (state, action) => {
        state.loading = false;
        const index = state.machines.findIndex(m => m.machine_id === action.payload.machine_id);
        if (index !== -1) {
            state.machines[index] = action.payload;
        } else {
            state.machines.push(action.payload);
        }
      })
      .addCase(registerMachine.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Registration failed';
      })
      .addCase(deleteMachine.pending, (state) => {
        state.loading = true;
      })
      .addCase(deleteMachine.fulfilled, (state, action) => {
        state.loading = false;
        state.machines = state.machines.filter(m => m.machine_id !== action.payload);
        if (state.currentMachineId === action.payload) {
            state.currentMachineId = state.machines.length > 0 ? state.machines[0].machine_id : 'PUMP-001';
        }
      })
      .addCase(deleteMachine.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Deletion failed';
      })
      .addCase(fetchMachineConfig.fulfilled, (state, action) => {
        state.machineConfigs[action.payload.machineId] = action.payload.sensorsMeta;
      });
  },
});

export const { setCurrentMachineId } = machineSlice.actions;
export default machineSlice.reducer;
