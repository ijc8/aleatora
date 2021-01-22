import { configureStore } from '@reduxjs/toolkit';
import counterReducer from '../features/counter/counterSlice';
import reduxWebsocket from '@giantmachines/redux-websocket';

export default configureStore({
  reducer: {
    counter: counterReducer,
  },
  middleware: [reduxWebsocket()]
});
