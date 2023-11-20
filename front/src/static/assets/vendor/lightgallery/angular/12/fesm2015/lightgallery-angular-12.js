import * as i0 from '@angular/core';
import { Injectable, Component, Input, NgModule } from '@angular/core';
import lightGallery from 'lightgallery';

class LightgalleryService {
    constructor() { }
}
LightgalleryService.ɵfac = i0.ɵɵngDeclareFactory({ minVersion: "12.0.0", version: "12.2.16", ngImport: i0, type: LightgalleryService, deps: [], target: i0.ɵɵFactoryTarget.Injectable });
LightgalleryService.ɵprov = i0.ɵɵngDeclareInjectable({ minVersion: "12.0.0", version: "12.2.16", ngImport: i0, type: LightgalleryService, providedIn: 'root' });
i0.ɵɵngDeclareClassMetadata({ minVersion: "12.0.0", version: "12.2.16", ngImport: i0, type: LightgalleryService, decorators: [{
            type: Injectable,
            args: [{
                    providedIn: 'root',
                }]
        }], ctorParameters: function () { return []; } });

const LgMethods = {
    onAfterAppendSlide: 'lgAfterAppendSlide',
    onInit: 'lgInit',
    onHasVideo: 'lgHasVideo',
    onContainerResize: 'lgContainerResize',
    onUpdateSlides: 'lgUpdateSlides',
    onAfterAppendSubHtml: 'lgAfterAppendSubHtml',
    onBeforeOpen: 'lgBeforeOpen',
    onAfterOpen: 'lgAfterOpen',
    onSlideItemLoad: 'lgSlideItemLoad',
    onBeforeSlide: 'lgBeforeSlide',
    onAfterSlide: 'lgAfterSlide',
    onPosterClick: 'lgPosterClick',
    onDragStart: 'lgDragStart',
    onDragMove: 'lgDragMove',
    onDragEnd: 'lgDragEnd',
    onBeforeNextSlide: 'lgBeforeNextSlide',
    onBeforePrevSlide: 'lgBeforePrevSlide',
    onBeforeClose: 'lgBeforeClose',
    onAfterClose: 'lgAfterClose',
    onRotateLeft: 'lgRotateLeft',
    onRotateRight: 'lgRotateRight',
    onFlipHorizontal: 'lgFlipHorizontal',
    onFlipVertical: 'lgFlipVertical',
};
class LightgalleryComponent {
    constructor(_elementRef) {
        this._elementRef = _elementRef;
        this.lgInitialized = false;
        this._elementRef = _elementRef;
    }
    ngAfterViewChecked() {
        if (!this.lgInitialized) {
            this.registerEvents();
            this.LG = lightGallery(this._elementRef.nativeElement, this.settings);
            this.lgInitialized = true;
        }
    }
    ngOnDestroy() {
        this.LG.destroy();
        this.lgInitialized = false;
    }
    registerEvents() {
        if (this.onAfterAppendSlide) {
            this._elementRef.nativeElement.addEventListener(LgMethods.onAfterAppendSlide, ((event) => {
                this.onAfterAppendSlide &&
                    this.onAfterAppendSlide(event.detail);
            }));
        }
        if (this.onInit) {
            this._elementRef.nativeElement.addEventListener(LgMethods.onInit, ((event) => {
                this.onInit && this.onInit(event.detail);
            }));
        }
        if (this.onHasVideo) {
            this._elementRef.nativeElement.addEventListener(LgMethods.onHasVideo, ((event) => {
                this.onHasVideo && this.onHasVideo(event.detail);
            }));
        }
        if (this.onContainerResize) {
            this._elementRef.nativeElement.addEventListener(LgMethods.onContainerResize, ((event) => {
                this.onContainerResize &&
                    this.onContainerResize(event.detail);
            }));
        }
        if (this.onAfterAppendSubHtml) {
            this._elementRef.nativeElement.addEventListener(LgMethods.onAfterAppendSubHtml, ((event) => {
                this.onAfterAppendSubHtml &&
                    this.onAfterAppendSubHtml(event.detail);
            }));
        }
        if (this.onBeforeOpen) {
            this._elementRef.nativeElement.addEventListener(LgMethods.onBeforeOpen, ((event) => {
                this.onBeforeOpen && this.onBeforeOpen(event.detail);
            }));
        }
        if (this.onAfterOpen) {
            this._elementRef.nativeElement.addEventListener(LgMethods.onAfterOpen, ((event) => {
                this.onAfterOpen && this.onAfterOpen(event.detail);
            }));
        }
        if (this.onSlideItemLoad) {
            this._elementRef.nativeElement.addEventListener(LgMethods.onSlideItemLoad, ((event) => {
                this.onSlideItemLoad && this.onSlideItemLoad(event.detail);
            }));
        }
        if (this.onBeforeSlide) {
            this._elementRef.nativeElement.addEventListener(LgMethods.onBeforeSlide, ((event) => {
                this.onBeforeSlide && this.onBeforeSlide(event.detail);
            }));
        }
        if (this.onAfterSlide) {
            this._elementRef.nativeElement.addEventListener(LgMethods.onAfterSlide, ((event) => {
                this.onAfterSlide && this.onAfterSlide(event.detail);
            }));
        }
        if (this.onPosterClick) {
            this._elementRef.nativeElement.addEventListener(LgMethods.onPosterClick, ((event) => {
                this.onPosterClick && this.onPosterClick(event.detail);
            }));
        }
        if (this.onDragStart) {
            this._elementRef.nativeElement.addEventListener(LgMethods.onDragStart, ((event) => {
                this.onDragStart && this.onDragStart(event.detail);
            }));
        }
        if (this.onDragMove) {
            this._elementRef.nativeElement.addEventListener(LgMethods.onDragMove, ((event) => {
                this.onDragMove && this.onDragMove(event.detail);
            }));
        }
        if (this.onDragEnd) {
            this._elementRef.nativeElement.addEventListener(LgMethods.onDragEnd, ((event) => {
                this.onDragEnd && this.onDragEnd(event.detail);
            }));
        }
        if (this.onBeforeNextSlide) {
            this._elementRef.nativeElement.addEventListener(LgMethods.onBeforeNextSlide, ((event) => {
                this.onBeforeNextSlide &&
                    this.onBeforeNextSlide(event.detail);
            }));
        }
        if (this.onBeforePrevSlide) {
            this._elementRef.nativeElement.addEventListener(LgMethods.onBeforePrevSlide, ((event) => {
                this.onBeforePrevSlide &&
                    this.onBeforePrevSlide(event.detail);
            }));
        }
        if (this.onBeforeClose) {
            this._elementRef.nativeElement.addEventListener(LgMethods.onBeforeClose, ((event) => {
                this.onBeforeClose && this.onBeforeClose(event.detail);
            }));
        }
        if (this.onAfterClose) {
            this._elementRef.nativeElement.addEventListener(LgMethods.onAfterClose, ((event) => {
                this.onAfterClose && this.onAfterClose(event.detail);
            }));
        }
        if (this.onRotateLeft) {
            this._elementRef.nativeElement.addEventListener(LgMethods.onRotateLeft, ((event) => {
                this.onRotateLeft && this.onRotateLeft(event.detail);
            }));
        }
        if (this.onRotateRight) {
            this._elementRef.nativeElement.addEventListener(LgMethods.onRotateRight, ((event) => {
                this.onRotateRight && this.onRotateRight(event.detail);
            }));
        }
        if (this.onFlipHorizontal) {
            this._elementRef.nativeElement.addEventListener(LgMethods.onFlipHorizontal, ((event) => {
                this.onFlipHorizontal &&
                    this.onFlipHorizontal(event.detail);
            }));
        }
        if (this.onFlipVertical) {
            this._elementRef.nativeElement.addEventListener(LgMethods.onFlipVertical, ((event) => {
                this.onFlipVertical && this.onFlipVertical(event.detail);
            }));
        }
    }
}
LightgalleryComponent.ɵfac = i0.ɵɵngDeclareFactory({ minVersion: "12.0.0", version: "12.2.16", ngImport: i0, type: LightgalleryComponent, deps: [{ token: i0.ElementRef }], target: i0.ɵɵFactoryTarget.Component });
LightgalleryComponent.ɵcmp = i0.ɵɵngDeclareComponent({ minVersion: "12.0.0", version: "12.2.16", type: LightgalleryComponent, selector: "lightgallery", inputs: { settings: "settings", onAfterAppendSlide: "onAfterAppendSlide", onInit: "onInit", onHasVideo: "onHasVideo", onContainerResize: "onContainerResize", onAfterAppendSubHtml: "onAfterAppendSubHtml", onBeforeOpen: "onBeforeOpen", onAfterOpen: "onAfterOpen", onSlideItemLoad: "onSlideItemLoad", onBeforeSlide: "onBeforeSlide", onAfterSlide: "onAfterSlide", onPosterClick: "onPosterClick", onDragStart: "onDragStart", onDragMove: "onDragMove", onDragEnd: "onDragEnd", onBeforeNextSlide: "onBeforeNextSlide", onBeforePrevSlide: "onBeforePrevSlide", onBeforeClose: "onBeforeClose", onAfterClose: "onAfterClose", onRotateLeft: "onRotateLeft", onRotateRight: "onRotateRight", onFlipHorizontal: "onFlipHorizontal", onFlipVertical: "onFlipVertical" }, ngImport: i0, template: '<ng-content></ng-content>', isInline: true });
i0.ɵɵngDeclareClassMetadata({ minVersion: "12.0.0", version: "12.2.16", ngImport: i0, type: LightgalleryComponent, decorators: [{
            type: Component,
            args: [{
                    selector: 'lightgallery',
                    template: '<ng-content></ng-content>',
                    styles: [],
                }]
        }], ctorParameters: function () { return [{ type: i0.ElementRef }]; }, propDecorators: { settings: [{
                type: Input
            }], onAfterAppendSlide: [{
                type: Input
            }], onInit: [{
                type: Input
            }], onHasVideo: [{
                type: Input
            }], onContainerResize: [{
                type: Input
            }], onAfterAppendSubHtml: [{
                type: Input
            }], onBeforeOpen: [{
                type: Input
            }], onAfterOpen: [{
                type: Input
            }], onSlideItemLoad: [{
                type: Input
            }], onBeforeSlide: [{
                type: Input
            }], onAfterSlide: [{
                type: Input
            }], onPosterClick: [{
                type: Input
            }], onDragStart: [{
                type: Input
            }], onDragMove: [{
                type: Input
            }], onDragEnd: [{
                type: Input
            }], onBeforeNextSlide: [{
                type: Input
            }], onBeforePrevSlide: [{
                type: Input
            }], onBeforeClose: [{
                type: Input
            }], onAfterClose: [{
                type: Input
            }], onRotateLeft: [{
                type: Input
            }], onRotateRight: [{
                type: Input
            }], onFlipHorizontal: [{
                type: Input
            }], onFlipVertical: [{
                type: Input
            }] } });

class LightgalleryModule {
}
LightgalleryModule.ɵfac = i0.ɵɵngDeclareFactory({ minVersion: "12.0.0", version: "12.2.16", ngImport: i0, type: LightgalleryModule, deps: [], target: i0.ɵɵFactoryTarget.NgModule });
LightgalleryModule.ɵmod = i0.ɵɵngDeclareNgModule({ minVersion: "12.0.0", version: "12.2.16", ngImport: i0, type: LightgalleryModule, declarations: [LightgalleryComponent], exports: [LightgalleryComponent] });
LightgalleryModule.ɵinj = i0.ɵɵngDeclareInjector({ minVersion: "12.0.0", version: "12.2.16", ngImport: i0, type: LightgalleryModule, imports: [[]] });
i0.ɵɵngDeclareClassMetadata({ minVersion: "12.0.0", version: "12.2.16", ngImport: i0, type: LightgalleryModule, decorators: [{
            type: NgModule,
            args: [{
                    declarations: [LightgalleryComponent],
                    imports: [],
                    exports: [LightgalleryComponent],
                }]
        }] });

/*
 * Public API Surface of lightgallery-angular
 */

/**
 * Generated bundle index. Do not edit.
 */

export { LightgalleryComponent, LightgalleryModule, LightgalleryService };
//# sourceMappingURL=lightgallery-angular-12.js.map
