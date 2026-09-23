import { apiService } from '../../services/api';

export async function withInitializeRetry<T>(request: () => Promise<T>, warning: string) {
  try {
    return await request();
  } catch (error) {
    console.warn(warning, error);
    await apiService.initialize();
    return request();
  }
}
