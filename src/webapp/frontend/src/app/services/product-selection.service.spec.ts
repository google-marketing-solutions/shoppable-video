import {signal} from '@angular/core';
import {TestBed} from '@angular/core/testing';
import {of} from 'rxjs';
import {MatchedProduct, Status, VideoAnalysis} from '../models';
import {AuthService, UserProfile} from './auth.service';
import {DataService} from './data.service';
import {ProductSelectionService} from './product-selection.service';

describe('ProductSelectionService', () => {
  let service: ProductSelectionService;
  let mockDataService: jasmine.SpyObj<DataService>;
  let mockAuthService: Partial<AuthService>;

  beforeEach(() => {
    mockDataService = jasmine.createSpyObj('DataService', ['updateCandidates']);
    mockAuthService = {
      user: signal<UserProfile | null>({
        email: 'test@example.com',
        picture: 'pic',
        name: 'Test User',
      }),
    };

    TestBed.configureTestingModule({
      providers: [
        ProductSelectionService,
        {provide: DataService, useValue: mockDataService},
        {provide: AuthService, useValue: mockAuthService},
      ],
    });
    service = TestBed.inject(ProductSelectionService);
  });

  it('should include user email in updateStatus', () => {
    const mockVideo: VideoAnalysis = {
      video: {
        uuid: 'video-uuid',
        source: '',
        videoId: null,
        gcsUri: null,
        md5Hash: null
      },
      identifiedProducts: []
    };
    const mockMatch: MatchedProduct = {
      matchedProductOfferId: 'offer-id',
      status: 'UNREVIEWED',
      matchedProductTitle: '',
      matchedProductBrand: '',
      timestamp: '',
      distance: 0
    };
    const productUuid = 'product-uuid';

    service.toggleSelection(mockVideo, productUuid, mockMatch);

    mockDataService.updateCandidates.and.returnValue(of({}));

    service.updateStatus(Status.APPROVED);

    expect(mockDataService.updateCandidates).toHaveBeenCalled();
    const args = mockDataService.updateCandidates.calls.mostRecent().args[0];
    expect(args.length).toBe(1);
    expect(args[0].candidateStatus.user).toBe('test@example.com');
  });
});
